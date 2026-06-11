import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import CACHE_FILE, DATA_DIR, MODEL_VERSION, RAW_DIR


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def empty_cache() -> Dict[str, Any]:
    return {
        "model_version": MODEL_VERSION,
        "generated_at": None,
        "sources": [],
        "matches": [],
        "tournament": {
            "simulations": 0,
            "stage_probabilities": [],
            "predicted_stages": [],
            "projected_matches": [],
            "matchup_rounds": [],
            "group_tables": [],
            "notes": [],
        },
        "filters": {"rounds": [], "teams": [], "statuses": [], "confidence_levels": []},
        "teams": {},
        "summary": {
            "match_count": 0,
            "team_count": 0,
            "result_rows": 0,
            "world_cup_rows": 0,
            "world_cup_local_signal_available": False,
            "market_signal_available": False,
            "betting_signal_available": False,
        },
        "error": None,
    }


def load_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    cache_path = path or CACHE_FILE
    if not cache_path.exists():
        return empty_cache()
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return empty_cache()
    baseline = empty_cache()
    baseline.update(payload)
    return baseline


def save_cache(payload: Dict[str, Any], path: Optional[Path] = None) -> None:
    ensure_data_dirs()
    cache_path = path or CACHE_FILE
    tmp_path = cache_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(cache_path)


def save_raw(filename: str, content: str) -> None:
    ensure_data_dirs()
    (RAW_DIR / filename).write_text(content, encoding="utf-8")


def read_raw(filename: str) -> Optional[str]:
    path = RAW_DIR / filename
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None
