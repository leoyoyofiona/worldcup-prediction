import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .cache import empty_cache, load_cache, now_iso, save_cache
from .config import MODEL_VERSION, UPDATE_JOB_TIMEOUT_SECONDS
from .live_results import sync_live_results
from .model import build_predictions, match_status, match_summary
from .sources import authorized_source_statuses, fetch_sources, load_cached_sources


AUTO_SYNC_INTERVAL_SECONDS = 300
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
DAILY_BETTING_BUDGET = 100.0


class PredictionService:
    def __init__(self) -> None:
        self._build_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._task_state: Dict[str, Any] = {
            "running": False,
            "kind": None,
            "message": None,
            "started_at": None,
            "finished_at": None,
            "error": None,
        }

    def start_update(self) -> Dict[str, Any]:
        return self._start_background_task(
            "update",
            "正在联网更新公开数据源并重新计算模型，完成后页面会自动刷新。",
            self._update_job,
        )

    def start_recalculate(self) -> Dict[str, Any]:
        return self._start_background_task(
            "recalculate",
            "正在使用本地缓存重新计算模型，完成后页面会自动刷新。",
            self._recalculate_job,
        )

    def _start_background_task(self, kind: str, message: str, target) -> Dict[str, Any]:
        if not self._build_lock.acquire(blocking=False):
            payload = self.status()
            payload["accepted"] = False
            payload["message"] = "已有更新或重新计算任务正在运行，请稍后刷新页面。"
            return payload

        with self._state_lock:
            self._task_state = {
                "running": True,
                "kind": kind,
                "message": message,
                "started_at": now_iso(),
                "finished_at": None,
                "error": None,
            }

        thread = threading.Thread(target=self._run_background_task, args=(target,), daemon=True)
        thread.start()

        payload = self.status()
        payload["accepted"] = True
        payload["message"] = message
        return payload

    def _run_background_task(self, target) -> None:
        try:
            target()
            error = None
        except Exception as exc:
            error = str(exc)
            previous = load_cache()
            previous["error"] = f"后台任务失败，继续使用旧预测：{exc}" if previous.get("matches") else str(exc)
            save_cache(previous)
        finally:
            with self._state_lock:
                self._task_state["running"] = False
                self._task_state["message"] = "后台任务已完成" if error is None else "后台任务失败"
                self._task_state["finished_at"] = now_iso()
                self._task_state["error"] = error
            self._build_lock.release()

    def _update_job(self) -> None:
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(lambda: asyncio.run(fetch_sources()))
            raw_payloads, statuses = future.result(timeout=UPDATE_JOB_TIMEOUT_SECONDS)
        except (FutureTimeoutError, Exception) as exc:
            raw_payloads, statuses = load_cached_sources()
            statuses.append(
                {
                    "id": "update_timeout_fallback",
                    "name": "联网更新整体超时保护",
                    "url": "",
                    "required": False,
                    "ok": True,
                    "status": "ok",
                    "message": f"联网更新超过 {UPDATE_JOB_TIMEOUT_SECONDS:.0f} 秒，已改用本地缓存重新计算：{exc}",
                    "bytes": 0,
                    "using_cache": True,
                    "fetched_at": now_iso(),
                }
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        rebuilt = self._build_or_cache(raw_payloads, statuses)
        rebuilt.setdefault("summary", {})["full_data_updated_at"] = now_iso()
        save_cache(sync_live_results(rebuilt))

    def _recalculate_job(self) -> None:
        raw_payloads, statuses = load_cached_sources()
        rebuilt = self._build_or_cache(raw_payloads, statuses)
        rebuilt.setdefault("summary", {})["local_model_recalculated_at"] = now_iso()
        save_cache(sync_live_results(rebuilt))

    def status(self) -> Dict[str, Any]:
        cache = self._cache_with_auto_sync()
        return {
            "model_version": cache.get("model_version"),
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "error": cache.get("error"),
            "source_count": len(cache.get("sources", [])),
            "task": self._task_snapshot(),
        }

    def sources(self) -> List[Dict[str, Any]]:
        sources = self._cache_with_auto_sync().get("sources", [])
        existing = {source.get("id") for source in sources}
        return sources + [source for source in authorized_source_statuses() if source.get("id") not in existing]

    def matches(self) -> Dict[str, Any]:
        cache = self._cache_with_auto_sync()
        matches = sorted(
            cache.get("matches", []),
            key=lambda match: (match.get("starts_at") or "9999-12-31T23:59:59+00:00", match.get("index") or 0),
        )
        return {
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "filters": cache.get("filters", {}),
            "matches": [match_summary(match) for match in matches],
            "tournament": cache.get("tournament", {}),
            "performance": cache.get("performance", {}),
            "error": cache.get("error"),
            "task": self._task_snapshot(),
        }

    def betting_daily(self) -> Dict[str, Any]:
        cache = self._cache_with_auto_sync()
        day_rows = build_betting_days(cache.get("matches", []), DAILY_BETTING_BUDGET)
        return {
            "generated_at": cache.get("generated_at"),
            "model_version": cache.get("model_version"),
            "days": day_rows,
            "current_day": day_rows[0] if day_rows else None,
            "note": "金额为按每日 100 元示例预算生成的模型参考，不是收益保证；若接入真实体彩赔率，会优先使用真实赔率计算超额水位、去水概率、EV 和可能奖金。",
            "task": self._task_snapshot(),
        }

    def tournament(self) -> Dict[str, Any]:
        cache = self._cache_with_auto_sync()
        return {
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "tournament": cache.get("tournament", {}),
            "error": cache.get("error"),
            "task": self._task_snapshot(),
        }

    def match_detail(self, match_id: str) -> Dict[str, Any]:
        cache = self._cache_with_auto_sync()
        for match in cache.get("matches", []):
            if match.get("id") == match_id:
                detail = dict(match)
                detail["sources"] = cache.get("sources", [])
                detail["generated_at"] = cache.get("generated_at")
                detail["model_version"] = cache.get("model_version")
                return detail
        raise KeyError(match_id)

    def _task_snapshot(self) -> Dict[str, Any]:
        with self._state_lock:
            return deepcopy(self._task_state)

    def _cache_with_auto_sync(self) -> Dict[str, Any]:
        cache = load_cache()
        if not self._should_auto_sync(cache):
            return cache
        if not self._build_lock.acquire(blocking=False):
            return cache
        with self._state_lock:
            self._task_state = {
                "running": True,
                "kind": "auto_sync",
                "message": "正在自动同步最新赛果并刷新预测。",
                "started_at": now_iso(),
                "finished_at": None,
                "error": None,
            }
        try:
            cache = sync_live_results(cache)
            save_cache(cache)
            error = None
        except Exception as exc:
            error = str(exc)
            cache["error"] = f"自动同步失败，继续使用旧预测：{exc}"
        finally:
            with self._state_lock:
                self._task_state["running"] = False
                self._task_state["message"] = "自动同步已完成" if error is None else "自动同步失败"
                self._task_state["finished_at"] = now_iso()
                self._task_state["error"] = error
            self._build_lock.release()
        return cache

    def _should_auto_sync(self, cache: Dict[str, Any]) -> bool:
        if not cache.get("matches"):
            return False
        synced_at = cache.get("summary", {}).get("live_result_synced_at")
        if not synced_at:
            return True
        try:
            parsed = datetime.fromisoformat(str(synced_at).replace("Z", "+00:00"))
        except ValueError:
            return True
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
        return age.total_seconds() >= AUTO_SYNC_INTERVAL_SECONDS

    def _build_or_cache(self, raw_payloads: Dict[str, str], statuses: List[Dict[str, object]]) -> Dict[str, Any]:
        try:
            payload = build_predictions(raw_payloads, statuses)
        except Exception as exc:
            previous = load_cache()
            if previous.get("matches"):
                previous["sources"] = statuses
                previous["error"] = f"本次更新失败，继续使用旧预测：{exc}"
                save_cache(previous)
                return previous
            payload = empty_cache()
            payload["sources"] = statuses
            payload["error"] = str(exc)
        save_cache(payload)
        return payload


service = PredictionService()


def beijing_datetime(match: Dict[str, Any]) -> Optional[datetime]:
    starts_at = match.get("starts_at")
    if not starts_at:
        return None
    try:
        parsed = datetime.fromisoformat(str(starts_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(BEIJING_TZ)


def beijing_date_key(match: Dict[str, Any]) -> str:
    parsed = beijing_datetime(match)
    if parsed:
        return parsed.date().isoformat()
    return str(match.get("date") or "待定")


def build_betting_days(
    matches: List[Dict[str, Any]],
    budget: float,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    now_utc = now or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_beijing = now_utc.astimezone(BEIJING_TZ)
    today_key = now_beijing.date().isoformat()
    candidates = sorted(
        [
            match
            for match in matches
            if is_betting_candidate(match, now_utc)
        ],
        key=lambda match: (match.get("starts_at") or "9999-12-31T23:59:59+00:00", match.get("index") or 0),
    )
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for match in candidates:
        grouped.setdefault(beijing_date_key(match), []).append(betting_match_payload(match, now_utc))
    if not grouped:
        return []
    selected_days = [today_key] if today_key in grouped else [min(grouped)]
    return [
        {
            "date": day,
            "timezone": "Asia/Shanghai",
            "budget": budget,
            "matches": attach_betting_recommendations(grouped[day], budget),
        }
        for day in selected_days
    ]


def is_betting_candidate(match: Dict[str, Any], now_utc: datetime) -> bool:
    if not match.get("teams_confirmed") or not match.get("betting_analysis"):
        return False
    if match.get("actual_score"):
        return False
    parsed = beijing_datetime(match)
    if parsed is None:
        return False
    starts_utc = parsed.astimezone(timezone.utc)
    if starts_utc <= now_utc - timedelta(hours=2, minutes=30):
        return False
    return True


def betting_match_payload(match: Dict[str, Any], now_utc: datetime) -> Dict[str, Any]:
    parsed = beijing_datetime(match)
    starts_utc = parsed.astimezone(timezone.utc) if parsed else None
    bettable = bool(starts_utc and starts_utc > now_utc)
    return {
        "id": match.get("id"),
        "round": match.get("round"),
        "group": match.get("group"),
        "date": match.get("date"),
        "beijing_date": beijing_date_key(match),
        "starts_at": match.get("starts_at"),
        "status": match_status_at(match.get("starts_at"), now_utc),
        "bettable": bettable,
        "actual_score": match.get("actual_score"),
        "team1": match.get("team1"),
        "team2": match.get("team2"),
        "predicted_score": match.get("predicted_score"),
        "confidence_label": match.get("confidence_label"),
        "probabilities": match.get("probabilities"),
        "betting_analysis": match.get("betting_analysis"),
    }


def attach_betting_recommendations(rows: List[Dict[str, Any]], budget: float) -> List[Dict[str, Any]]:
    weighted: List[tuple[float, Dict[str, Any]]] = []
    for row in rows:
        if row.get("bettable") is False:
            weighted.append((0.0, row))
            continue
        analysis = row.get("betting_analysis") or {}
        probabilities = analysis.get("model_probabilities") or row.get("probabilities") or {}
        if not probabilities:
            weight = 1.0
        else:
            values = sorted([float(value or 0.0) for value in probabilities.values()], reverse=True)
            gap = (values[0] - values[1]) if len(values) > 1 else values[0]
            weight = max(0.8, gap / 10.0)
        weighted.append((weight, row))

    total_weight = sum(weight for weight, row in weighted if row.get("bettable") is not False) or 1.0
    for index, (weight, row) in enumerate(weighted):
        if row.get("bettable") is False:
            row["betting_recommendation"] = build_betting_recommendation(row, 0.0)
            row["betting_recommendation"]["risk_note"] = "比赛已开赛，不建议再按赛前投注方案投注。"
            continue
        raw_stake = budget * weight / total_weight
        stake = max(2.0, round(raw_stake / 2.0) * 2.0)
        remaining_bettable = [item for _, item in weighted[index + 1 :] if item.get("bettable") is not False]
        if not remaining_bettable:
            used = sum(float(item.get("betting_recommendation", {}).get("stake", 0.0)) for _, item in weighted[:index])
            stake = max(2.0, round((budget - used) / 2.0) * 2.0)
        row["betting_recommendation"] = build_betting_recommendation(row, stake)
    return [row for _, row in weighted]


def match_status_at(starts_at: Optional[str], now_utc: datetime) -> str:
    if not starts_at:
        return "时间待定"
    try:
        starts = datetime.fromisoformat(str(starts_at).replace("Z", "+00:00"))
    except ValueError:
        return "时间待定"
    if starts.tzinfo is None:
        starts = starts.replace(tzinfo=timezone.utc)
    starts = starts.astimezone(timezone.utc)
    if now_utc < starts:
        return "未开赛"
    if now_utc <= starts + timedelta(hours=2, minutes=30):
        return "进行中"
    return "已结束"


def build_betting_recommendation(row: Dict[str, Any], stake: float) -> Dict[str, Any]:
    analysis = row.get("betting_analysis") or {}
    probabilities = analysis.get("model_probabilities") or row.get("probabilities") or {}
    favorite = analysis.get("favorite") or max(probabilities, key=probabilities.get)
    labels = {
        "team1_win": row.get("team1"),
        "draw": "平局",
        "team2_win": row.get("team2"),
    }
    fair_odds = analysis.get("fair_odds") or {}
    threshold_odds = analysis.get("value_threshold_odds") or {}
    quoted_odds = analysis.get("quoted_odds") or {}
    odds = float(quoted_odds.get(favorite) or threshold_odds.get(favorite) or fair_odds.get(favorite) or 1.0)
    possible_payout = round(stake * odds, 2)
    possible_profit = round(possible_payout - stake, 2)
    return {
        "play_type": "竞彩足球胜平负",
        "selection": labels.get(favorite, favorite),
        "outcome_key": favorite,
        "stake": round(stake, 2),
        "reference_odds": round(odds, 2),
        "odds_type": "真实赔率" if favorite in quoted_odds else "建议最低参考赔率",
        "possible_payout": possible_payout,
        "possible_profit": possible_profit,
        "risk_note": "按模型概率和参考赔率估算，实际出票赔率、过关方式、税费规则和赛果会改变奖金。",
    }
