import asyncio
import threading
from copy import deepcopy
from typing import Any, Dict, List

from .cache import load_cache, now_iso, save_cache
from .model import build_predictions, match_summary
from .sources import fetch_sources, load_cached_sources


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
            "正在联网抓取数据并重建模型，完成后页面会自动刷新。",
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
        raw_payloads, statuses = asyncio.run(fetch_sources())
        self._build_or_cache(raw_payloads, statuses)

    def _recalculate_job(self) -> None:
        raw_payloads, statuses = load_cached_sources()
        self._build_or_cache(raw_payloads, statuses)

    def status(self) -> Dict[str, Any]:
        cache = load_cache()
        return {
            "model_version": cache.get("model_version"),
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "error": cache.get("error"),
            "source_count": len(cache.get("sources", [])),
            "task": self._task_snapshot(),
        }

    def sources(self) -> List[Dict[str, Any]]:
        return load_cache().get("sources", [])

    def matches(self) -> Dict[str, Any]:
        cache = load_cache()
        return {
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "filters": cache.get("filters", {}),
            "matches": [match_summary(match) for match in cache.get("matches", [])],
            "tournament": cache.get("tournament", {}),
            "error": cache.get("error"),
            "task": self._task_snapshot(),
        }

    def tournament(self) -> Dict[str, Any]:
        cache = load_cache()
        return {
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "tournament": cache.get("tournament", {}),
            "error": cache.get("error"),
            "task": self._task_snapshot(),
        }

    def match_detail(self, match_id: str) -> Dict[str, Any]:
        cache = load_cache()
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
