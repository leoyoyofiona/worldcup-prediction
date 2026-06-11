import threading
from typing import Any, Dict, List

from .cache import empty_cache, load_cache, save_cache
from .model import build_predictions, match_summary
from .sources import fetch_sources, load_cached_sources


class PredictionService:
    def __init__(self) -> None:
        self._build_lock = threading.Lock()

    async def update(self) -> Dict[str, Any]:
        if not self._build_lock.acquire(blocking=False):
            return self._busy_payload()
        try:
            raw_payloads, statuses = await fetch_sources()
            return self._build_or_cache(raw_payloads, statuses)
        finally:
            self._build_lock.release()

    def recalculate(self) -> Dict[str, Any]:
        if not self._build_lock.acquire(blocking=False):
            return self._busy_payload()
        try:
            raw_payloads, statuses = load_cached_sources()
            return self._build_or_cache(raw_payloads, statuses)
        finally:
            self._build_lock.release()

    def status(self) -> Dict[str, Any]:
        cache = load_cache()
        return {
            "model_version": cache.get("model_version"),
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "error": cache.get("error"),
            "source_count": len(cache.get("sources", [])),
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
        }

    def tournament(self) -> Dict[str, Any]:
        cache = load_cache()
        return {
            "generated_at": cache.get("generated_at"),
            "summary": cache.get("summary", {}),
            "tournament": cache.get("tournament", {}),
            "error": cache.get("error"),
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

    def _busy_payload(self) -> Dict[str, Any]:
        payload = load_cache()
        if not payload.get("matches"):
            payload = empty_cache()
        payload["error"] = "已有更新或重新计算任务正在运行，请稍后刷新页面。"
        return payload

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
