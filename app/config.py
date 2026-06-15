import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_FILE = DATA_DIR / "cache.json"
ACTUAL_RESULTS_FILE = DATA_DIR / "actual_results.json"

MODEL_VERSION = "0.1.5"
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
TOURNAMENT_SIMULATIONS = int(os.getenv("TOURNAMENT_SIMULATIONS", "50000"))
LOCAL_WORLDCUP_MATCHES_PATHS = [
    ROOT_DIR / "WorldCupMatches.csv",
    ROOT_DIR / "data" / "WorldCupMatches.csv",
    Path("/Users/leo/Downloads/世界杯数据/WorldCupMatches.csv"),
]
