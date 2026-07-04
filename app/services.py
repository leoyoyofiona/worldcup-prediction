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

    def status(self, force_sync: bool = False) -> Dict[str, Any]:
        cache = self._cache_with_auto_sync(force_sync=force_sync)
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
        day_rows = build_betting_days(cache.get("matches", []))
        return {
            "generated_at": cache.get("generated_at"),
            "model_version": cache.get("model_version"),
            "days": day_rows,
            "current_day": day_rows[0] if day_rows else None,
            "note": "以下按北京时间当日未完赛比赛生成总进球数、比分、半全场和爆冷观察；仅供赛前分析和理性观赛参考，不构成购彩保证。",
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

    def _cache_with_auto_sync(self, force_sync: bool = False) -> Dict[str, Any]:
        cache = load_cache()
        if not self._should_auto_sync(cache, force_sync=force_sync):
            return cache
        if not self._build_lock.acquire(blocking=False):
            return cache
        self._start_auto_sync_task(cache)
        return cache

    def _start_auto_sync_task(self, cache: Dict[str, Any]) -> None:
        with self._state_lock:
            self._task_state = {
                "running": True,
                "kind": "auto_sync",
                "message": "正在自动同步最新赛果并刷新预测。",
                "started_at": now_iso(),
                "finished_at": None,
                "error": None,
            }
        thread = threading.Thread(target=self._run_background_task, args=(lambda: self._auto_sync_job(cache),), daemon=True)
        thread.start()

    def _auto_sync_job(self, cache: Dict[str, Any]) -> None:
        save_cache(sync_live_results(cache))

    def _should_auto_sync(self, cache: Dict[str, Any], force_sync: bool = False) -> bool:
        if not cache.get("matches"):
            return False
        if force_sync:
            return True
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
    days = []
    for day in selected_days:
        days.append(
            {
                "date": day,
                "timezone": "Asia/Shanghai",
                "recommendation_types": ["总进球数", "比分", "半全场", "爆冷观察"],
                "matches": grouped[day],
            }
        )
    return days


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
        "expected_goals": match.get("expected_goals"),
        "score_summary": match.get("score_summary"),
        "probabilities": match.get("probabilities"),
        "betting_analysis": match.get("betting_analysis"),
        "daily_recommendation": build_daily_match_recommendation(match),
    }


def build_daily_match_recommendation(match: Dict[str, Any]) -> Dict[str, Any]:
    probabilities = probability_map(match)
    favorite_key = max(probabilities, key=probabilities.get) if probabilities else "team1_win"
    favorite_probability = probabilities.get(favorite_key, 0.0)
    second_probability = sorted(probabilities.values(), reverse=True)[1] if len(probabilities) > 1 else 0.0
    confidence = confidence_from_probability_gap(favorite_probability, favorite_probability - second_probability)
    return {
        "total_goals": build_total_goals_pick(match),
        "score": build_score_pick(match),
        "half_full": build_half_full_pick(match, favorite_key, confidence),
        "upset": build_upset_pick(match, favorite_key),
    }


def probability_map(match: Dict[str, Any]) -> Dict[str, float]:
    analysis = match.get("betting_analysis") or {}
    raw = analysis.get("model_probabilities") or match.get("probabilities") or {}
    return {
        key: safe_float(raw.get(key), 0.0)
        for key in ("team1_win", "draw", "team2_win")
    }


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def confidence_from_probability_gap(probability: float, gap: float) -> str:
    if probability >= 64.0 and gap >= 24.0:
        return "高"
    if probability >= 48.0 and gap >= 10.0:
        return "中"
    return "观察"


def build_total_goals_pick(match: Dict[str, Any]) -> Dict[str, Any]:
    summary = match.get("score_summary") or {}
    expected = match.get("expected_goals") or {}
    expected_total = safe_float(
        summary.get("expected_total_goals"),
        safe_float(expected.get("team1")) + safe_float(expected.get("team2")),
    )
    over_25 = safe_float(summary.get("over_2_5"))
    over_35 = safe_float(summary.get("over_3_5"))
    both_score = safe_float(summary.get("both_teams_score"))
    if expected_total >= 3.6 or over_35 >= 58.0:
        selection = "4球及以上"
        confidence = "高" if over_35 >= 62.0 else "中"
    elif expected_total >= 2.75 or over_25 >= 58.0:
        selection = "3球左右"
        confidence = "中"
    elif expected_total <= 2.15 or over_25 <= 42.0:
        selection = "0-2球"
        confidence = "中"
    else:
        selection = "2-3球"
        confidence = "观察"
    return {
        "play_type": "总进球数",
        "selection": selection,
        "confidence": confidence,
        "expected_total_goals": round(expected_total, 2),
        "over_2_5": round(over_25, 1),
        "over_3_5": round(over_35, 1),
        "both_teams_score": round(both_score, 1),
        "reason": f"总 xG {expected_total:.2f}，大2.5概率 {over_25:.1f}%，双方进球 {both_score:.1f}%。",
    }


def build_score_pick(match: Dict[str, Any]) -> Dict[str, Any]:
    summary = match.get("score_summary") or {}
    primary = str(summary.get("representative_score") or match.get("predicted_score") or "待定")
    modal = str(summary.get("modal_score") or primary)
    expected = match.get("expected_goals") or {}
    secondary = modal if modal != primary else ""
    return {
        "play_type": "比分",
        "selection": primary,
        "secondary": secondary,
        "confidence": "观察",
        "reason": (
            f"xG {safe_float(expected.get('team1')):.2f}:{safe_float(expected.get('team2')):.2f}"
            + (f"，精确众数比分 {modal}。" if modal and modal != primary else "。")
        ),
    }


def build_half_full_pick(match: Dict[str, Any], favorite_key: str, confidence: str) -> Dict[str, Any]:
    probabilities = probability_map(match)
    total_expected = safe_float((match.get("score_summary") or {}).get("expected_total_goals"))
    draw_probability = probabilities.get("draw", 0.0)
    favorite_probability = probabilities.get(favorite_key, 0.0)
    if favorite_key == "draw" or (draw_probability >= 30.0 and favorite_probability < 48.0):
        selection = "平平"
        reason = f"平局概率 {draw_probability:.1f}%，双方差距不大。"
    elif favorite_key == "team1_win":
        selection = "胜胜" if favorite_probability >= 62.0 and total_expected >= 2.7 else "平胜"
        reason = f"{match.get('team1')} 取胜概率 {favorite_probability:.1f}%，上半场按谨慎节奏估计。"
    else:
        selection = "负负" if favorite_probability >= 62.0 and total_expected >= 2.7 else "平负"
        reason = f"{match.get('team2')} 取胜概率 {favorite_probability:.1f}%，上半场按谨慎节奏估计。"
    return {
        "play_type": "半全场",
        "selection": selection,
        "confidence": confidence,
        "reason": reason,
    }


def build_upset_pick(match: Dict[str, Any], favorite_key: str) -> Dict[str, Any]:
    probabilities = probability_map(match)
    analysis = match.get("betting_analysis") or {}
    threshold_odds = analysis.get("value_threshold_odds") or {}
    labels = {
        "team1_win": match.get("team1") or "第一队",
        "draw": "平局",
        "team2_win": match.get("team2") or "第二队",
    }
    favorite_probability = probabilities.get(favorite_key, 0.0)
    candidates = [(key, value) for key, value in probabilities.items() if key != favorite_key]
    cold_key, cold_probability = max(candidates, key=lambda item: item[1]) if candidates else ("draw", 0.0)
    if favorite_probability >= 66.0 and cold_probability < 22.0:
        selection = "爆冷风险低"
        confidence = "高"
        reason = f"热门方向概率 {favorite_probability:.1f}%，最大冷门方向 {labels[cold_key]} 仅 {cold_probability:.1f}%。"
    elif cold_key == "draw":
        selection = "防平"
        confidence = "中" if cold_probability >= 24.0 else "观察"
        reason = f"平局概率 {cold_probability:.1f}%，适合列为冷门观察项。"
    else:
        selection = f"关注{labels[cold_key]}爆冷"
        confidence = "观察"
        reason = f"{labels[cold_key]} 概率 {cold_probability:.1f}%，属于低概率高波动方向。"
    value_odds = threshold_odds.get(cold_key)
    if value_odds:
        reason = f"{reason} 公开赔率高于 {safe_float(value_odds):.2f} 时才进入价值观察。"
    return {
        "play_type": "爆冷观察",
        "selection": selection,
        "outcome_key": cold_key,
        "probability": round(cold_probability, 1),
        "value_threshold_odds": round(safe_float(value_odds), 2) if value_odds else None,
        "confidence": confidence,
        "reason": reason,
    }


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
