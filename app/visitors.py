import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from .cache import ensure_data_dirs, now_iso
from .config import VISITOR_BASELINE_COUNT, VISITOR_BASELINE_SINCE, VISITOR_STATS_FILE


_lock = threading.Lock()
BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def record_visit(path: Optional[Path] = None) -> Dict[str, Any]:
    with _lock:
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
        return _public_stats(_load_stats(path))


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
