import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List

from .cache import empty_cache, load_cache, now_iso, save_cache
from .config import MODEL_VERSION, UPDATE_JOB_TIMEOUT_SECONDS
from .live_results import sync_live_results
from .model import build_predictions, match_summary
from .sources import fetch_sources, load_cached_sources


AUTO_SYNC_INTERVAL_SECONDS = 300


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
        return self._cache_with_auto_sync().get("sources", [])

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
        matches = sorted(
            [
                match
                for match in cache.get("matches", [])
                if match.get("teams_confirmed") and not match.get("actual_score") and match.get("betting_analysis")
            ],
            key=lambda match: (match.get("starts_at") or "9999-12-31T23:59:59+00:00", match.get("index") or 0),
        )
        days: Dict[str, List[Dict[str, Any]]] = {}
        for match in matches:
            day = str(match.get("date") or (match.get("starts_at") or "")[:10] or "待定")
            days.setdefault(day, []).append(
                {
                    "id": match.get("id"),
                    "round": match.get("round"),
                    "group": match.get("group"),
                    "date": match.get("date"),
                    "starts_at": match.get("starts_at"),
                    "team1": match.get("team1"),
                    "team2": match.get("team2"),
                    "predicted_score": match.get("predicted_score"),
                    "confidence_label": match.get("confidence_label"),
                    "probabilities": match.get("probabilities"),
                    "betting_analysis": match.get("betting_analysis"),
                }
            )
        day_rows = [{"date": day, "matches": rows} for day, rows in days.items()]
        return {
            "generated_at": cache.get("generated_at"),
            "model_version": cache.get("model_version"),
            "days": day_rows,
            "current_day": day_rows[0] if day_rows else None,
            "note": "当前未接入逐场真实胜平负赔率；页面先给出模型公平赔率和价值赔率门槛。若后续接入授权赔率，会自动计算超额水位、去水概率和价值差。",
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
