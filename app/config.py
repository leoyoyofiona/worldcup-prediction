import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_FILE = DATA_DIR / "cache.json"
ACTUAL_RESULTS_FILE = DATA_DIR / "actual_results.json"
VISITOR_STATS_FILE = DATA_DIR / "visitor_stats.json"

MODEL_VERSION = "0.3.3"
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
UPDATE_JOB_TIMEOUT_SECONDS = float(os.getenv("UPDATE_JOB_TIMEOUT_SECONDS", "45"))
TOURNAMENT_SIMULATIONS = int(os.getenv("TOURNAMENT_SIMULATIONS", "50000"))
VISITOR_BASELINE_COUNT = int(os.getenv("VISITOR_BASELINE_COUNT", "10"))
VISITOR_BASELINE_SINCE = os.getenv("VISITOR_BASELINE_SINCE", "2026-07-01")
VISITOR_COUNTER_BACKEND = os.getenv("VISITOR_COUNTER_BACKEND", "local")
VISITOR_COUNTER_KEY = os.getenv("VISITOR_COUNTER_KEY", "worldcup_prediction_peur_7a9d4a4f")
LOCAL_WORLDCUP_MATCHES_PATHS = [
    ROOT_DIR / "WorldCupMatches.csv",
    ROOT_DIR / "data" / "WorldCupMatches.csv",
    Path("/Users/leo/Downloads/世界杯数据/WorldCupMatches.csv"),
]
