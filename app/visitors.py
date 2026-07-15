import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

import httpx

from .cache import ensure_data_dirs, now_iso
from .config import (
    VISITOR_BASELINE_COUNT,
    VISITOR_BASELINE_SINCE,
    VISITOR_COUNTER_BACKEND,
    VISITOR_COUNTER_KEY,
    VISITOR_STATS_FILE,
)


_lock = threading.Lock()
BEIJING_TZ = ZoneInfo("Asia/Shanghai")
COUNTAPI_BASE_URL = "https://countapi.mileshilliard.com/api/v1"


def record_visit(path: Optional[Path] = None) -> Dict[str, Any]:
    with _lock:
        if path is None and _external_counter_enabled():
            external = _record_external_visit()
            if external:
                _mirror_external_stats(external)
                return external
        stats = _load_stats(path)
        today = _today_key()
        stats["tracked_visits"] = int(stats.get("tracked_visits") or 0) + 1
        stats["today_visits"] = int(stats.get("daily", {}).get(today) or 0) + 1
        stats.setdefault("daily", {})[today] = stats["today_visits"]
        stats["last_visit_at"] = now_iso()
        _save_stats(stats, path)
        return _public_stats(stats)


def visitor_stats(path: Optional[Path] = None) -> Dict[str, Any]:
    with _lock:
        if path is None and _external_counter_enabled():
            external = _external_stats()
            if external:
                return external
        return _public_stats(_load_stats(path))


def ensure_minimum_total(min_total: int, path: Optional[Path] = None) -> Dict[str, Any]:
    with _lock:
        stats = _load_stats(path)
        baseline_count = int(stats.get("baseline_count") or 0)
        tracked_visits = int(stats.get("tracked_visits") or 0)
        required_tracked = max(0, int(min_total or 0) - baseline_count)
        if required_tracked > tracked_visits:
            stats["tracked_visits"] = required_tracked
            today = _today_key()
            stats.setdefault("daily", {})[today] = max(int(stats.get("daily", {}).get(today) or 0), required_tracked)
            stats["today_visits"] = int(stats["daily"][today])
            stats["last_visit_at"] = now_iso()
            _save_stats(stats, path)
        return _public_stats(stats)


def _load_stats(path: Optional[Path] = None) -> Dict[str, Any]:
    stats_path = path or VISITOR_STATS_FILE
    if not stats_path.exists():
        return _empty_stats()
    try:
        payload = json.loads(stats_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_stats()
    baseline = _empty_stats()
    baseline.update(payload)
    if not isinstance(baseline.get("daily"), dict):
        baseline["daily"] = {}
    return baseline


def _save_stats(stats: Dict[str, Any], path: Optional[Path] = None) -> None:
    ensure_data_dirs()
    stats_path = path or VISITOR_STATS_FILE
    tmp_path = stats_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(stats_path)


def _empty_stats() -> Dict[str, Any]:
    return {
        "baseline_count": max(0, VISITOR_BASELINE_COUNT),
        "baseline_since": VISITOR_BASELINE_SINCE,
        "tracked_visits": 0,
        "today_visits": 0,
        "daily": {},
        "last_visit_at": None,
    }


def _public_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    today = _today_key()
    baseline_count = int(stats.get("baseline_count") or 0)
    tracked_visits = int(stats.get("tracked_visits") or 0)
    today_visits = int((stats.get("daily") or {}).get(today) or 0)
    return {
        "total_visits": baseline_count + tracked_visits,
        "baseline_count": baseline_count,
        "tracked_visits": tracked_visits,
        "today_visits": today_visits,
        "baseline_since": stats.get("baseline_since") or VISITOR_BASELINE_SINCE,
        "last_visit_at": stats.get("last_visit_at"),
        "note": "访问次数按页面打开计数；不记录个人身份信息。历史真实访问量需由上线前已有日志或平台统计提供。",
    }


def _today_key() -> str:
    return datetime.now(timezone.utc).astimezone(BEIJING_TZ).date().isoformat()


def _external_counter_enabled() -> bool:
    return VISITOR_COUNTER_BACKEND.lower() == "countapi" and bool(VISITOR_COUNTER_KEY)


def _record_external_visit() -> Optional[Dict[str, Any]]:
    total_value = _countapi_request("hit", _total_key())
    today_value = _countapi_request("hit", _today_key_name())
    if total_value is None or today_value is None:
        return None
    return _external_public_stats(total_value, today_value, now_iso())


def _external_stats() -> Optional[Dict[str, Any]]:
    total_value = _countapi_request("get", _total_key())
    today_value = _countapi_request("get", _today_key_name())
    if total_value is None:
        return None
    return _external_public_stats(total_value, today_value or 0, None)


def _countapi_request(action: str, key: str) -> Optional[int]:
    try:
        response = httpx.get(f"{COUNTAPI_BASE_URL}/{action}/{key}", timeout=4.0)
        if response.status_code == 404 and action == "get":
            return 0
        response.raise_for_status()
        value = response.json().get("value")
        return int(value)
    except Exception:
        return None


def _external_public_stats(tracked_visits: int, today_visits: int, last_visit_at: Optional[str]) -> Dict[str, Any]:
    baseline_count = max(0, VISITOR_BASELINE_COUNT)
    return {
        "total_visits": baseline_count + max(0, tracked_visits),
        "baseline_count": baseline_count,
        "tracked_visits": max(0, tracked_visits),
        "today_visits": max(0, today_visits),
        "baseline_since": VISITOR_BASELINE_SINCE,
        "last_visit_at": last_visit_at,
        "persistent": True,
        "note": "访问次数按页面打开计数，使用外部持久计数器保存；不记录个人身份信息。",
    }


def _mirror_external_stats(stats: Dict[str, Any]) -> None:
    local_stats = {
        "baseline_count": stats.get("baseline_count", 0),
        "baseline_since": stats.get("baseline_since", VISITOR_BASELINE_SINCE),
        "tracked_visits": stats.get("tracked_visits", 0),
        "today_visits": stats.get("today_visits", 0),
        "daily": {_today_key(): stats.get("today_visits", 0)},
        "last_visit_at": stats.get("last_visit_at"),
    }
    try:
        _save_stats(local_stats)
    except Exception:
        pass


def _total_key() -> str:
    return f"{VISITOR_COUNTER_KEY}_total"


def _today_key_name() -> str:
    return f"{VISITOR_COUNTER_KEY}_day_{_today_key()}"
