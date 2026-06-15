import csv
import html
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

from .cache import now_iso
from .config import ACTUAL_RESULTS_FILE, MODEL_VERSION, TOURNAMENT_SIMULATIONS


HOST_TEAMS = {"United States", "Mexico", "Canada"}

OFF_FIELD_FACTORS: Dict[str, Sequence[Dict[str, Any]]] = {
    "England": [
        {
            "name": "装备运输失窃扰动",
            "adjustment": -8.0,
            "description": "训练装备失窃后大部分已追回，按轻微备战扰动处理。",
            "source_name": "CBS Sports / Guardian",
            "source_url": "https://www.cbssports.com/soccer/news/england-gear-stolen-from-kansas-city-team-camp-ahead-of-world-cup-campaign-reportedly-recovered/",
        }
    ],
    "Iran": [
        {
            "name": "签证与入境不确定性",
            "adjustment": -18.0,
            "description": "美国入境、签证和随队人员限制带来旅行与后勤不确定性。",
            "source_name": "Guardian / ESPN / American Immigration Council",
            "source_url": "https://www.theguardian.com/football/2026/jun/06/iran-world-cup-visas-mexico",
        }
    ],
}

OFF_FIELD_MAX_ABS_ADJUSTMENT = 24.0

TEAM_ALIASES: Dict[str, Sequence[str]] = {
    "United States": ["USA", "USMNT", "United States of America", "U.S.A.", "U.S."],
    "South Korea": ["Korea Republic", "Republic of Korea", "Korea, Republic of"],
    "North Korea": ["Korea DPR", "DPR Korea"],
    "Czech Republic": ["Czechia", "Czechoslovakia"],
    "Bosnia & Herzegovina": ["Bosnia-Herzegovina", "Bosnia and Herzegovina", "Bosnia"],
    "Germany": ["Germany FR", "West Germany", "German DR"],
    "Russia": ["Soviet Union"],
    "Serbia": ["Yugoslavia", "Serbia and Montenegro"],
    "Ivory Coast": ["Cote d'Ivoire", "Côte d'Ivoire"],
    "DR Congo": ["Congo DR", "Democratic Republic of Congo", "Congo-Kinshasa"],
    "Republic of Ireland": ["Ireland"],
    "China": ["China PR", "PR China"],
    "Iran": ["IR Iran"],
    "Cape Verde": ["Cabo Verde"],
    "Curacao": ["Curaçao"],
}

TEAM_CHINESE_ALIASES: Dict[str, Sequence[str]] = {
    "Argentina": ["阿根廷"],
    "Australia": ["澳大利亚"],
    "Austria": ["奥地利"],
    "Belgium": ["比利时"],
    "Brazil": ["巴西"],
    "Canada": ["加拿大"],
    "Chile": ["智利"],
    "China": ["中国队", "中国男足"],
    "Colombia": ["哥伦比亚"],
    "Croatia": ["克罗地亚"],
    "Czech Republic": ["捷克", "捷克队"],
    "Denmark": ["丹麦"],
    "Ecuador": ["厄瓜多尔"],
    "Egypt": ["埃及"],
    "England": ["英格兰"],
    "France": ["法国"],
    "Germany": ["德国"],
    "Ghana": ["加纳"],
    "Iran": ["伊朗"],
    "Italy": ["意大利"],
    "Japan": ["日本"],
    "Mexico": ["墨西哥"],
    "Morocco": ["摩洛哥"],
    "Netherlands": ["荷兰", "尼德兰"],
    "Nigeria": ["尼日利亚"],
    "Norway": ["挪威"],
    "Poland": ["波兰"],
    "Portugal": ["葡萄牙"],
    "Qatar": ["卡塔尔"],
    "Saudi Arabia": ["沙特", "沙特阿拉伯"],
    "Senegal": ["塞内加尔"],
    "Serbia": ["塞尔维亚"],
    "South Africa": ["南非"],
    "South Korea": ["韩国"],
    "Spain": ["西班牙"],
    "Switzerland": ["瑞士"],
    "Turkey": ["土耳其"],
    "Ukraine": ["乌克兰"],
    "United States": ["美国", "美国队"],
    "Uruguay": ["乌拉圭"],
    "Uzbekistan": ["乌兹别克斯坦"],
}

MARKET_KEYWORDS = [
    "世界杯",
    "足球",
    "球衣",
    "国旗",
    "围巾",
    "订单",
    "热销",
    "爆单",
    "外贸",
    "义乌",
    "周边",
    "world cup",
    "jersey",
    "flag",
    "orders",
]

BETTING_KEYWORDS = [
    "odds",
    "bookmaker",
    "sportsbook",
    "betting",
    "outright",
    "winner",
    "futures",
    "price",
    "handicap",
    "moneyline",
    "world cup",
    "盘口",
    "赔率",
    "博彩",
    "让球",
]

BETTING_SOURCE_IDS = [
    "oddsjet_europe",
    "oddsjet_asia",
    "oddsjet_oceania",
    "oddsjet_africa",
    "oddsjet_north_america",
    "oddsjet_south_america",
    "comparebet_uk",
]

GROUP_LETTERS = list("ABCDEFGHIJKL")
TOURNAMENT_RANDOM_SEED = 20260603

TEAM_CONFEDERATIONS = {
    "Algeria": "CAF",
    "Argentina": "CONMEBOL",
    "Australia": "AFC",
    "Austria": "UEFA",
    "Belgium": "UEFA",
    "Bosnia & Herzegovina": "UEFA",
    "Brazil": "CONMEBOL",
    "Canada": "CONCACAF",
    "Cape Verde": "CAF",
    "Colombia": "CONMEBOL",
    "Croatia": "UEFA",
    "Curacao": "CONCACAF",
    "Czech Republic": "UEFA",
    "DR Congo": "CAF",
    "Ecuador": "CONMEBOL",
    "Egypt": "CAF",
    "England": "UEFA",
    "France": "UEFA",
    "Germany": "UEFA",
    "Ghana": "CAF",
    "Haiti": "CONCACAF",
    "Iran": "AFC",
    "Iraq": "AFC",
    "Ivory Coast": "CAF",
    "Japan": "AFC",
    "Jordan": "AFC",
    "Mexico": "CONCACAF",
    "Morocco": "CAF",
    "Netherlands": "UEFA",
    "New Zealand": "OFC",
    "Norway": "UEFA",
    "Panama": "CONCACAF",
    "Paraguay": "CONMEBOL",
    "Portugal": "UEFA",
    "Qatar": "AFC",
    "Saudi Arabia": "AFC",
    "Scotland": "UEFA",
    "Senegal": "CAF",
    "South Africa": "CAF",
    "South Korea": "AFC",
    "Spain": "UEFA",
    "Sweden": "UEFA",
    "Switzerland": "UEFA",
    "Tunisia": "CAF",
    "Turkey": "UEFA",
    "United States": "CONCACAF",
    "Uruguay": "CONMEBOL",
    "Uzbekistan": "AFC",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_team(value: str) -> str:
    value = strip_accents(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def alias_index(known_teams: Optional[Iterable[str]] = None) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for canonical, aliases in TEAM_ALIASES.items():
        index[normalize_team(canonical)] = canonical
        for alias in aliases:
            index[normalize_team(alias)] = canonical
    if known_teams:
        for team in known_teams:
            index.setdefault(normalize_team(team), team)
    return index


def canonicalize_team(team: str, known_teams: Optional[Iterable[str]] = None) -> str:
    if not team:
        return team
    index = alias_index(known_teams)
    return index.get(normalize_team(team), team.strip())


def clean_text(raw: str) -> str:
    raw = html.unescape(raw or "")
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def parse_match_datetime(match_date: str, match_time: str) -> Optional[str]:
    if not match_date:
        return None
    time_text = match_time or "00:00 UTC+0"
    match = re.search(r"(\d{1,2}:\d{2})\s*UTC\s*([+-]\d{1,2})", time_text)
    try:
        if match:
            hour_text, offset_text = match.groups()
            offset = timezone(timedelta(hours=int(offset_text)))
            dt = datetime.strptime(f"{match_date} {hour_text}", "%Y-%m-%d %H:%M").replace(tzinfo=offset)
        else:
            dt = datetime.strptime(match_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def match_status(starts_at: Optional[str]) -> str:
    if not starts_at:
        return "时间待定"
    try:
        starts = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
    except ValueError:
        return "时间待定"
    now = datetime.now(timezone.utc)
    if now < starts:
        return "未开赛"
    if now <= starts + timedelta(hours=2, minutes=30):
        return "进行中"
    return "已结束"


def score_from_schedule_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    score_pairs = [
        ("score1", "score2"),
        ("team1_score", "team2_score"),
        ("home_score", "away_score"),
        ("goals1", "goals2"),
        ("home_goals", "away_goals"),
    ]
    for key1, key2 in score_pairs:
        if key1 in item and key2 in item:
            goals1 = safe_int(item.get(key1, ""))
            goals2 = safe_int(item.get(key2, ""))
            if goals1 is not None and goals2 is not None:
                return {"team1": goals1, "team2": goals2, "score": f"{goals1}-{goals2}"}

    raw_score = item.get("score") or item.get("result") or item.get("final_score")
    if isinstance(raw_score, str):
        match = re.search(r"(\d+)\s*[-:]\s*(\d+)", raw_score)
        if match:
            goals1 = int(match.group(1))
            goals2 = int(match.group(2))
            return {"team1": goals1, "team2": goals2, "score": f"{goals1}-{goals2}"}

    return None


def safe_int_value(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return safe_int(str(value))


def parse_schedule(raw_json: str) -> List[Dict[str, Any]]:
    parsed = json.loads(raw_json)
    matches = parsed.get("matches", [])
    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(matches, start=1):
        team1 = (item.get("team1") or item.get("home_team") or "").strip()
        team2 = (item.get("team2") or item.get("away_team") or "").strip()
        starts_at = parse_match_datetime(item.get("date", ""), item.get("time", ""))
        round_name = item.get("round") or "赛程"
        group_name = item.get("group") or ""
        actual_score = score_from_schedule_item(item)
        is_knockout = not group_name and bool(
            re.search(r"round of|quarter|semi|final|third", round_name, re.IGNORECASE)
        )
        normalized.append(
            {
                "id": f"wc2026-{index:03d}",
                "index": index,
                "round": round_name,
                "group": group_name,
                "stage": group_name or round_name,
                "date": item.get("date") or "",
                "time": item.get("time") or "",
                "starts_at": starts_at,
                "team1": team1,
                "team2": team2,
                "ground": item.get("ground") or "",
                "status": match_status(starts_at),
                "is_knockout": is_knockout,
                "actual_score": actual_score,
            }
        )
    return normalized


def safe_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_results_csv(raw_csv: str, known_teams: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    reader = csv.DictReader(StringIO(raw_csv))
    today = date.today()
    for row in reader:
        home_score = safe_int(row.get("home_score", ""))
        away_score = safe_int(row.get("away_score", ""))
        if home_score is None or away_score is None:
            continue
        try:
            match_date = datetime.strptime(row.get("date", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        if match_date > today:
            continue
        rows.append(
            {
                "date": match_date,
                "home_team": canonicalize_team(row.get("home_team", ""), known_teams),
                "away_team": canonicalize_team(row.get("away_team", ""), known_teams),
                "home_score": home_score,
                "away_score": away_score,
                "tournament": row.get("tournament") or "",
                "neutral": str(row.get("neutral", "")).upper() == "TRUE",
            }
        )
    rows.sort(key=lambda item: item["date"])
    return rows


def parse_world_cup_match_date(value: str, year: str) -> Optional[date]:
    text = (value or "").split("-")[0].strip()
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    safe_year = safe_int(year)
    if safe_year is None:
        return None
    return date(safe_year, 1, 1)


def parse_world_cup_matches_csv(raw_csv: str, known_teams: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not raw_csv:
        return rows
    reader = csv.DictReader(StringIO(raw_csv))
    for row in reader:
        home_score = safe_int(row.get("Home Team Goals", ""))
        away_score = safe_int(row.get("Away Team Goals", ""))
        match_date = parse_world_cup_match_date(row.get("Datetime", ""), row.get("Year", ""))
        home_team = canonicalize_team(row.get("Home Team Name", ""), known_teams)
        away_team = canonicalize_team(row.get("Away Team Name", ""), known_teams)
        if home_score is None or away_score is None or match_date is None or not home_team or not away_team:
            continue
        rows.append(
            {
                "date": match_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "tournament": "FIFA World Cup",
                "stage": row.get("Stage") or "",
                "neutral": True,
                "source": "worldcup_matches_local",
            }
        )
    rows.sort(key=lambda item: item["date"])
    return rows


def merge_results(primary: Sequence[Dict[str, Any]], extra: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for result in list(primary) + list(extra):
        key = (
            result.get("date"),
            result.get("home_team"),
            result.get("away_team"),
            result.get("home_score"),
            result.get("away_score"),
        )
        reverse_key = (
            result.get("date"),
            result.get("away_team"),
            result.get("home_team"),
            result.get("away_score"),
            result.get("home_score"),
        )
        if key in seen or reverse_key in seen:
            continue
        seen.add(key)
        merged.append(result)
    merged.sort(key=lambda item: item["date"])
    return merged


def tournament_k(tournament: str) -> float:
    text = tournament.lower()
    if "fifa world cup" in text and "qualification" not in text:
        return 48.0
    if "qualification" in text or "qualifier" in text:
        return 34.0
    if any(name in text for name in ["uefa euro", "copa", "africa cup", "asian cup", "gold cup"]):
        return 40.0
    if "friendly" in text:
        return 18.0
    return 26.0


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_competitive_match(result: Dict[str, Any]) -> bool:
    tournament = (result.get("tournament") or "").lower()
    return "friendly" not in tournament


def is_world_cup_final_tournament(result: Dict[str, Any]) -> bool:
    tournament = (result.get("tournament") or "").lower()
    return "fifa world cup" in tournament and "qualification" not in tournament


def world_cup_stage_weight(stage: str) -> float:
    text = (stage or "").lower()
    if "final" in text and "third" not in text:
        return 2.25
    if "semi" in text:
        return 1.85
    if "quarter" in text:
        return 1.55
    if "round of 16" in text:
        return 1.3
    if "third" in text:
        return 1.25
    return 1.0


def is_world_cup_knockout_stage(stage: str) -> bool:
    text = (stage or "").lower()
    return any(token in text for token in ["round of 16", "quarter", "semi", "final", "third"])


def build_world_cup_profiles(results: Sequence[Dict[str, Any]], schedule_teams: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    teams = {team for team in schedule_teams if team}
    accum: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    current_year = date.today().year
    for result in results:
        stage = result.get("stage", "")
        weight = world_cup_stage_weight(stage)
        age = max(0, current_year - result["date"].year)
        recency = clamp(math.pow(0.5, age / 28.0), 0.16, 1.0)
        weighted_stage = weight * recency
        knockout = is_world_cup_knockout_stage(stage)
        final_stage = "final" in (stage or "").lower() and "third" not in (stage or "").lower()
        semi_stage = "semi" in (stage or "").lower()

        home = result["home_team"]
        away = result["away_team"]
        teams.update([home, away])
        home_score = result["home_score"]
        away_score = result["away_score"]
        if home_score > away_score:
            home_points, away_points = 3.0, 0.0
            home_knockout_win, away_knockout_win = 1.0, 0.0
        elif home_score == away_score:
            home_points, away_points = 1.0, 1.0
            home_knockout_win, away_knockout_win = 0.0, 0.0
        else:
            home_points, away_points = 0.0, 3.0
            home_knockout_win, away_knockout_win = 0.0, 1.0

        for team, points, gf, ga, knockout_win in (
            (home, home_points, home_score, away_score, home_knockout_win),
            (away, away_points, away_score, home_score, away_knockout_win),
        ):
            row = accum[team]
            row["matches"] += 1.0
            row["weighted_matches"] += weighted_stage
            row["weighted_points"] += points * weighted_stage
            row["weighted_gf"] += gf * weighted_stage
            row["weighted_ga"] += ga * weighted_stage
            if knockout:
                row["knockout_matches"] += 1.0
                row["weighted_knockout_matches"] += weighted_stage
                row["weighted_knockout_wins"] += knockout_win * weighted_stage
            if semi_stage:
                row["semi_apps"] += recency
            if final_stage:
                row["final_apps"] += recency

    profiles: Dict[str, Dict[str, Any]] = {}
    for team in sorted(teams):
        row = accum.get(team, {})
        weighted_matches = float(row.get("weighted_matches", 0.0))
        if weighted_matches <= 0:
            profiles[team] = {
                "world_cup_local_matches": 0,
                "world_cup_weighted_matches": 0.0,
                "world_cup_stage_points_rate": 0.0,
                "world_cup_stage_goal_diff": 0.0,
                "world_cup_knockout_matches": 0,
                "world_cup_knockout_win_rate": 0.0,
                "world_cup_stage_adjustment": 0.0,
                "world_cup_stage_attack": 1.0,
                "world_cup_stage_defense": 1.0,
            }
            continue
        points_rate = float(row["weighted_points"]) / (3.0 * weighted_matches)
        goal_diff = (float(row["weighted_gf"]) - float(row["weighted_ga"])) / weighted_matches
        gf_avg = float(row["weighted_gf"]) / weighted_matches
        ga_avg = float(row["weighted_ga"]) / weighted_matches
        weighted_knockout_matches = float(row.get("weighted_knockout_matches", 0.0))
        knockout_win_rate = (
            float(row.get("weighted_knockout_wins", 0.0)) / weighted_knockout_matches
            if weighted_knockout_matches
            else 0.0
        )
        late_round_bonus = min(float(row.get("semi_apps", 0.0)) * 3.5 + float(row.get("final_apps", 0.0)) * 5.5, 18.0)
        adjustment = clamp(
            (points_rate - 0.42) * 58.0 + goal_diff * 9.5 + (knockout_win_rate - 0.32) * 18.0 + late_round_bonus,
            -35.0,
            45.0,
        )
        profiles[team] = {
            "world_cup_local_matches": int(row.get("matches", 0.0)),
            "world_cup_weighted_matches": round(weighted_matches, 1),
            "world_cup_stage_points_rate": round(points_rate, 3),
            "world_cup_stage_goal_diff": round(goal_diff, 2),
            "world_cup_knockout_matches": int(row.get("knockout_matches", 0.0)),
            "world_cup_knockout_win_rate": round(knockout_win_rate, 3),
            "world_cup_stage_adjustment": round(adjustment, 1),
            "world_cup_stage_attack": round(clamp((gf_avg + 0.7) / 2.05, 0.65, 1.65), 3),
            "world_cup_stage_defense": round(clamp((ga_avg + 0.7) / 2.05, 0.65, 1.65), 3),
        }
    return profiles


def confederation_for_team(team: str) -> Optional[str]:
    return TEAM_CONFEDERATIONS.get(canonicalize_team(team))


def home_continent_adjustment(team: str) -> float:
    return 12.0 if confederation_for_team(team) == "CONCACAF" else 0.0


def build_team_stats(
    results: Sequence[Dict[str, Any]],
    schedule_teams: Iterable[str],
    world_cup_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    teams = {team for team in schedule_teams if team}
    ratings: Dict[str, float] = defaultdict(lambda: 1500.0)
    recent: Dict[str, Deque[Dict[str, float]]] = defaultdict(lambda: deque(maxlen=10))
    goal_form: Dict[str, Deque[Tuple[int, int]]] = defaultdict(lambda: deque(maxlen=20))
    competitive_recent: Dict[str, Deque[Dict[str, float]]] = defaultdict(lambda: deque(maxlen=10))
    competitive_defense: Dict[str, Deque[Tuple[int, int]]] = defaultdict(lambda: deque(maxlen=5))
    world_cup_history: Dict[str, Deque[Dict[str, float]]] = defaultdict(lambda: deque(maxlen=16))
    match_counts: Counter[str] = Counter()
    total_goals = 0
    scored_team_matches = 0

    for result in results:
        home = result["home_team"]
        away = result["away_team"]
        if not home or not away:
            continue
        teams.add(home)
        teams.add(away)
        home_rating = ratings[home]
        away_rating = ratings[away]
        home_advantage = 0.0 if result["neutral"] else 55.0
        home_expected = expected_score(home_rating + home_advantage, away_rating)

        home_score = result["home_score"]
        away_score = result["away_score"]
        if home_score > away_score:
            home_actual = 1.0
            home_points, away_points = 3.0, 0.0
        elif home_score == away_score:
            home_actual = 0.5
            home_points, away_points = 1.0, 1.0
        else:
            home_actual = 0.0
            home_points, away_points = 0.0, 3.0

        goal_diff = abs(home_score - away_score)
        margin_multiplier = 1.0 + min(math.log(goal_diff + 1.0), 1.6) * 0.18
        change = tournament_k(result["tournament"]) * margin_multiplier * (home_actual - home_expected)
        ratings[home] = home_rating + change
        ratings[away] = away_rating - change

        recent[home].append({"points": home_points, "gf": float(home_score), "ga": float(away_score), "opp_elo": away_rating})
        recent[away].append({"points": away_points, "gf": float(away_score), "ga": float(home_score), "opp_elo": home_rating})
        goal_form[home].append((home_score, away_score))
        goal_form[away].append((away_score, home_score))
        if result["date"].year >= 1960 and is_competitive_match(result):
            competitive_recent[home].append({"points": home_points, "gf": float(home_score), "ga": float(away_score), "opp_elo": away_rating})
            competitive_recent[away].append({"points": away_points, "gf": float(away_score), "ga": float(home_score), "opp_elo": home_rating})
            competitive_defense[home].append((home_score, away_score))
            competitive_defense[away].append((away_score, home_score))
        if result["date"].year >= 1960 and is_world_cup_final_tournament(result):
            world_cup_history[home].append({"points": home_points, "gf": float(home_score), "ga": float(away_score)})
            world_cup_history[away].append({"points": away_points, "gf": float(away_score), "ga": float(home_score)})
        match_counts[home] += 1
        match_counts[away] += 1
        total_goals += home_score + away_score
        scored_team_matches += 2

    global_goals = total_goals / scored_team_matches if scored_team_matches else 1.35
    stats: Dict[str, Dict[str, Any]] = {}
    for team in sorted(teams):
        rec = list(recent[team])
        goals = list(goal_form[team])
        competitive = list(competitive_recent[team])
        competitive_last_defense = list(competitive_defense[team])
        world_cup = list(world_cup_history[team])
        if rec:
            points_norm = sum(item["points"] for item in rec) / (3.0 * len(rec))
            avg_gd = sum(item["gf"] - item["ga"] for item in rec) / len(rec)
            avg_opp = sum(item["opp_elo"] for item in rec) / len(rec)
            form_adjustment = clamp((points_norm - 0.5) * 70.0 + avg_gd * 18.0 + (avg_opp - 1500.0) * 0.025, -45.0, 45.0)
        else:
            points_norm = 0.5
            avg_gd = 0.0
            avg_opp = 1500.0
            form_adjustment = 0.0

        if goals:
            gf_avg = sum(gf for gf, _ in goals) / len(goals)
            ga_avg = sum(ga for _, ga in goals) / len(goals)
        else:
            gf_avg = global_goals
            ga_avg = global_goals
        if competitive:
            comp_points_norm = sum(item["points"] for item in competitive) / (3.0 * len(competitive))
            comp_gf_avg = sum(item["gf"] for item in competitive) / len(competitive)
            comp_ga_avg = sum(item["ga"] for item in competitive) / len(competitive)
            comp_gd_avg = comp_gf_avg - comp_ga_avg
            comp_opp_avg = sum(item["opp_elo"] for item in competitive) / len(competitive)
            competitive_adjustment = clamp(
                (comp_points_norm - 0.5) * 66.0 + comp_gd_avg * 20.0 + (comp_opp_avg - 1500.0) * 0.025,
                -45.0,
                45.0,
            )
        else:
            comp_points_norm = 0.5
            comp_gf_avg = gf_avg
            comp_ga_avg = ga_avg
            comp_gd_avg = 0.0
            comp_opp_avg = 1500.0
            competitive_adjustment = 0.0
        if competitive_last_defense:
            mandatory_defense_ga = sum(ga for _, ga in competitive_last_defense) / len(competitive_last_defense)
        else:
            mandatory_defense_ga = comp_ga_avg
        if world_cup:
            wc_points_norm = sum(item["points"] for item in world_cup) / (3.0 * len(world_cup))
            wc_gd_avg = sum(item["gf"] - item["ga"] for item in world_cup) / len(world_cup)
            world_cup_adjustment = clamp((wc_points_norm - 0.44) * 56.0 + wc_gd_avg * 12.0, -30.0, 35.0)
        else:
            wc_points_norm = 0.0
            wc_gd_avg = 0.0
            world_cup_adjustment = 0.0
        world_cup_profile = (world_cup_profiles or {}).get(team, {})
        world_cup_stage_adjustment = float(world_cup_profile.get("world_cup_stage_adjustment", 0.0))
        world_cup_stage_attack = float(world_cup_profile.get("world_cup_stage_attack", 1.0))
        world_cup_stage_defense = float(world_cup_profile.get("world_cup_stage_defense", 1.0))
        continent_adjustment = home_continent_adjustment(team)
        goldman_adjustment = clamp(
            competitive_adjustment * 0.52 + world_cup_adjustment * 0.85 + world_cup_stage_adjustment * 0.72 + continent_adjustment,
            -75.0,
            90.0,
        )
        attack = clamp((gf_avg + 0.7) / (global_goals + 0.7), 0.55, 1.75)
        defense = clamp((ga_avg + 0.7) / (global_goals + 0.7), 0.55, 1.75)
        mandatory_attack = clamp((comp_gf_avg + 0.7) / (global_goals + 0.7), 0.55, 1.85)
        mandatory_defense = clamp((mandatory_defense_ga + 0.7) / (global_goals + 0.7), 0.55, 1.85)
        goldman_attack = round(clamp(attack * 0.56 + mandatory_attack * 0.34 + world_cup_stage_attack * 0.10, 0.55, 1.8), 3)
        goldman_defense = round(clamp(defense * 0.52 + mandatory_defense * 0.38 + world_cup_stage_defense * 0.10, 0.55, 1.8), 3)
        stats[team] = {
            "team": team,
            "elo": round(ratings[team], 1),
            "matches": match_counts[team],
            "recent_points_rate": round(points_norm, 3),
            "recent_goal_diff": round(avg_gd, 2),
            "recent_opponent_elo": round(avg_opp, 1),
            "form_adjustment": round(form_adjustment, 1),
            "attack": round(attack, 3),
            "defense": round(defense, 3),
            "competitive_points_rate": round(comp_points_norm, 3),
            "competitive_goal_diff": round(comp_gd_avg, 2),
            "competitive_opponent_elo": round(comp_opp_avg, 1),
            "competitive_adjustment": round(competitive_adjustment, 1),
            "world_cup_points_rate": round(wc_points_norm, 3),
            "world_cup_goal_diff": round(wc_gd_avg, 2),
            "world_cup_adjustment": round(world_cup_adjustment, 1),
            "world_cup_stage_adjustment": round(world_cup_stage_adjustment, 1),
            "world_cup_stage_points_rate": world_cup_profile.get("world_cup_stage_points_rate", 0.0),
            "world_cup_stage_goal_diff": world_cup_profile.get("world_cup_stage_goal_diff", 0.0),
            "world_cup_local_matches": world_cup_profile.get("world_cup_local_matches", 0),
            "world_cup_knockout_matches": world_cup_profile.get("world_cup_knockout_matches", 0),
            "world_cup_knockout_win_rate": world_cup_profile.get("world_cup_knockout_win_rate", 0.0),
            "home_continent_adjustment": round(continent_adjustment, 1),
            "goldman_adjustment": round(goldman_adjustment, 1),
            "mandatory_attack": round(mandatory_attack, 3),
            "mandatory_defense": round(mandatory_defense, 3),
            "goldman_attack": goldman_attack,
            "goldman_defense": goldman_defense,
        }
    return stats


def team_aliases_for_text(team: str) -> List[str]:
    aliases = [team]
    aliases.extend(TEAM_ALIASES.get(team, []))
    aliases.extend(TEAM_CHINESE_ALIASES.get(team, []))
    return [alias for alias in aliases if alias]


def count_ascii_alias(text: str, alias: str) -> int:
    return len(re.findall(rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])", text))


def build_market_scores(teams: Iterable[str], raw_texts: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    cleaned = "\n".join(clean_text(text) for text in raw_texts if text)
    lowered = strip_accents(cleaned).lower()
    keyword_hits = sum(lowered.count(keyword.lower()) for keyword in MARKET_KEYWORDS)
    raw_scores: Dict[str, float] = {}
    mentions: Dict[str, int] = {}
    for team in teams:
        count = 0
        for alias in team_aliases_for_text(team):
            if re.search(r"[\u4e00-\u9fff]", alias):
                count += cleaned.count(alias)
            else:
                normalized_alias = strip_accents(alias).lower()
                if len(normalized_alias) >= 3:
                    count += count_ascii_alias(lowered, normalized_alias)
        mentions[team] = count
        raw_scores[team] = float(count)

    max_score = max(raw_scores.values()) if raw_scores else 0.0
    available = bool(cleaned and keyword_hits > 0 and max_score > 0)
    scores: Dict[str, Dict[str, Any]] = {}
    for team, raw in raw_scores.items():
        if not available:
            index = 0.0
            adjustment = 0.0
        else:
            index = raw / max_score if max_score else 0.0
            adjustment = clamp(index * 25.0, 0.0, 25.0)
        scores[team] = {
            "mentions": mentions[team],
            "index": round(index, 3),
            "adjustment": round(adjustment, 1),
            "available": available,
            "keyword_hits": keyword_hits,
        }
    return scores


def fractional_to_decimal(token: str) -> Optional[float]:
    match = re.fullmatch(r"(\d{1,3})/(\d{1,3})", token)
    if not match:
        return None
    numerator, denominator = int(match.group(1)), int(match.group(2))
    if denominator <= 0:
        return None
    return 1.0 + numerator / denominator


def american_to_decimal(token: str) -> Optional[float]:
    if not re.fullmatch(r"[+-]\d{3,5}", token):
        return None
    value = int(token)
    if value > 0:
        return 1.0 + value / 100.0
    if value < 0:
        return 1.0 + 100.0 / abs(value)
    return None


def decimal_odds_from_token(token: str) -> Optional[float]:
    token = token.strip()
    decimal = fractional_to_decimal(token) or american_to_decimal(token)
    if decimal is None:
        try:
            decimal = float(token)
        except ValueError:
            return None
    if 1.01 <= decimal <= 501.0:
        return decimal
    return None


def odds_in_window(window: str) -> List[float]:
    tokens = re.findall(r"(?<!\d)(?:[+-]\d{3,5}|\d{1,3}/\d{1,3}|\d{1,3}(?:\.\d{1,2})?)(?!\d)", window)
    odds: List[float] = []
    for token in tokens:
        decimal = decimal_odds_from_token(token)
        if decimal is not None:
            odds.append(decimal)
    return odds


def build_betting_scores(teams: Iterable[str], raw_texts: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    cleaned = "\n".join(clean_text(text) for text in raw_texts if text)
    lowered = strip_accents(cleaned).lower()
    keyword_hits = sum(lowered.count(keyword.lower()) for keyword in BETTING_KEYWORDS)
    team_rows: Dict[str, Dict[str, Any]] = {}
    raw_scores: Dict[str, float] = {}

    for team in teams:
        mentions = 0
        team_odds: List[float] = []
        for alias in team_aliases_for_text(team):
            if len(alias) < 3:
                continue
            if re.search(r"[\u4e00-\u9fff]", alias):
                pattern = re.escape(alias)
                source_text = cleaned
            else:
                pattern = rf"(?<![a-z0-9]){re.escape(strip_accents(alias).lower())}(?![a-z0-9])"
                source_text = lowered
            for match in re.finditer(pattern, source_text):
                mentions += 1
                start = match.start()
                end = min(len(source_text), match.end() + 110)
                team_odds.extend(odds_in_window(source_text[start:end]))

        best_odds = min(team_odds) if team_odds else None
        implied = 1.0 / best_odds if best_odds else 0.0
        raw_score = implied if implied else float(mentions) * 0.003
        raw_scores[team] = raw_score
        team_rows[team] = {
            "mentions": mentions,
            "odds_count": len(team_odds),
            "best_decimal_odds": round(best_odds, 2) if best_odds else None,
            "implied_probability": round(implied * 100.0, 2) if implied else 0.0,
            "keyword_hits": keyword_hits,
        }

    max_score = max(raw_scores.values()) if raw_scores else 0.0
    available = bool(cleaned and keyword_hits > 0 and max_score > 0)
    scores: Dict[str, Dict[str, Any]] = {}
    for team, row in team_rows.items():
        if available:
            index = raw_scores[team] / max_score if max_score else 0.0
            adjustment = clamp(index * 35.0, 0.0, 35.0)
        else:
            index = 0.0
            adjustment = 0.0
        scores[team] = {
            **row,
            "index": round(index, 3),
            "adjustment": round(adjustment, 1),
            "available": available,
        }
    return scores


def parse_fifa_rankings(raw_text: str, teams: Iterable[str]) -> Dict[str, int]:
    cleaned = clean_text(raw_text)
    rankings: Dict[str, int] = {}
    if not cleaned:
        return rankings
    for team in teams:
        best_rank: Optional[int] = None
        for alias in team_aliases_for_text(team):
            if len(alias) < 3:
                continue
            idx = cleaned.lower().find(alias.lower())
            if idx < 0:
                continue
            window = cleaned[max(0, idx - 120) : idx + 120]
            candidates = [int(item) for item in re.findall(r"\b([1-9]\d{0,2})\b", window)]
            candidates = [item for item in candidates if item <= 220]
            if candidates:
                best_rank = min(candidates) if best_rank is None else min(best_rank, min(candidates))
        if best_rank is not None:
            rankings[team] = best_rank
    if len(rankings) < 8:
        return {}
    return rankings


def ranking_adjustment(rank: Optional[int]) -> float:
    if rank is None:
        return 0.0
    return clamp((70.0 - float(rank)) * 0.55, -25.0, 30.0)


def poisson_probability(lam: float, goals: int) -> float:
    return math.exp(-lam) * math.pow(lam, goals) / math.factorial(goals)


def score_matrix(lambda1: float, lambda2: float, max_goals: int = 7) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    rows: List[Dict[str, Any]] = []
    totals = {"team1_win": 0.0, "draw": 0.0, "team2_win": 0.0}
    total_mass = 0.0
    for goals1 in range(max_goals + 1):
        p1 = poisson_probability(lambda1, goals1)
        for goals2 in range(max_goals + 1):
            probability = p1 * poisson_probability(lambda2, goals2)
            total_mass += probability
            if goals1 > goals2:
                totals["team1_win"] += probability
                outcome = "team1_win"
            elif goals1 == goals2:
                totals["draw"] += probability
                outcome = "draw"
            else:
                totals["team2_win"] += probability
                outcome = "team2_win"
            rows.append({"score": f"{goals1}-{goals2}", "goals1": goals1, "goals2": goals2, "outcome": outcome, "probability": probability})
    if total_mass > 0:
        for key in totals:
            totals[key] /= total_mass
        for row in rows:
            row["probability"] /= total_mass
    rows.sort(key=lambda item: item["probability"], reverse=True)
    return rows, totals


def is_placeholder_team(team: str) -> bool:
    text = (team or "").lower()
    upper_text = (team or "").upper().strip()
    if not text:
        return True
    if any(token in text for token in ["winner", "runner-up", "runner up", "tbd", "to be decided", "third"]):
        return True
    if re.fullmatch(r"[12][A-L]", upper_text):
        return True
    if re.fullmatch(r"3[A-L](?:/[A-L])+", upper_text):
        return True
    if re.fullmatch(r"[WL]\d{2,3}", upper_text):
        return True
    return False


def confidence_label(probabilities: Dict[str, float]) -> Tuple[float, str]:
    values = sorted(probabilities.values(), reverse=True)
    gap = values[0] - values[1] if len(values) > 1 else 0.0
    if gap >= 0.18:
        return gap, "高"
    if gap >= 0.08:
        return gap, "中"
    return gap, "低"


def pct(value: float) -> float:
    return round(value * 100.0, 1)


def select_representative_score(
    distribution: Sequence[Dict[str, Any]],
    probabilities_raw: Dict[str, float],
    expected_total: float,
) -> str:
    if not distribution:
        return "待定"
    modal_score = distribution[0]["score"]
    if expected_total < 2.35:
        return modal_score

    favorite_key = max(probabilities_raw, key=probabilities_raw.get)
    target_total = max(2, int(round(expected_total)))
    min_total = 2 if favorite_key == "draw" else target_total
    candidates = []
    for row in distribution[:36]:
        total_goals = int(row["goals1"]) + int(row["goals2"])
        if total_goals < min_total:
            continue
        if expected_total >= 2.8 and total_goals < target_total:
            continue
        outcome_penalty = 0.0 if row["outcome"] == favorite_key else 0.85
        total_penalty = abs(total_goals - expected_total) * 0.35
        probability_penalty = -math.log(max(float(row["probability"]), 1e-9))
        candidates.append((probability_penalty + outcome_penalty + total_penalty, row["score"]))
    if not candidates:
        return modal_score
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][1]


def score_distribution_summary(distribution: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    over_2_5 = 0.0
    over_3_5 = 0.0
    both_score = 0.0
    for row in distribution:
        goals1 = int(row["goals1"])
        goals2 = int(row["goals2"])
        probability = float(row["probability"])
        total = goals1 + goals2
        if total >= 3:
            over_2_5 += probability
        if total >= 4:
            over_3_5 += probability
        if goals1 > 0 and goals2 > 0:
            both_score += probability
    return {
        "over_2_5": pct(over_2_5),
        "over_3_5": pct(over_3_5),
        "both_teams_score": pct(both_score),
    }


def default_signal() -> Dict[str, Any]:
    return {"adjustment": 0.0, "index": 0.0, "mentions": 0, "available": False}


def off_field_signal(team: str) -> Dict[str, Any]:
    factors = list(OFF_FIELD_FACTORS.get(team, []))
    adjustment = clamp(sum(float(item.get("adjustment", 0.0)) for item in factors), -OFF_FIELD_MAX_ABS_ADJUSTMENT, OFF_FIELD_MAX_ABS_ADJUSTMENT)
    return {
        "adjustment": round(adjustment, 1),
        "available": bool(factors),
        "factors": factors,
    }


def rule_adaptation_adjustment(stat: Dict[str, Any]) -> float:
    attack = float(stat.get("goldman_attack", stat.get("attack", 1.0)))
    defense = float(stat.get("goldman_defense", stat.get("defense", 1.0)))
    competitive_rate = float(stat.get("competitive_points_rate", stat.get("recent_points_rate", 0.5)))
    # New restart countdowns, goalkeeper limits and scheduled water breaks are modeled as a small
    # adaptability signal: efficient attacks and organized defenses benefit slightly.
    adjustment = (attack - 1.0) * 12.0 + (1.0 - defense) * 10.0 + (competitive_rate - 0.5) * 12.0
    return round(clamp(adjustment, -14.0, 14.0), 1)


def context_attack_multiplier(components: Dict[str, float]) -> float:
    adjustment = components.get("off_field", 0.0) / 220.0 + components.get("rules", 0.0) / 420.0
    return clamp(1.0 + adjustment, 0.86, 1.12)


def context_defense_multiplier(components: Dict[str, float]) -> float:
    adjustment = -components.get("off_field", 0.0) / 360.0 - components.get("rules", 0.0) / 700.0
    return clamp(1.0 + adjustment, 0.92, 1.08)


def effective_team_rating(
    team: str,
    team_stats: Dict[str, Dict[str, Any]],
    market_scores: Dict[str, Dict[str, Any]],
    betting_scores: Dict[str, Dict[str, Any]],
    rankings: Dict[str, int],
) -> Tuple[float, Dict[str, float], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    stat = team_stats.get(team) or fallback_team_stat(team)
    market = market_scores.get(team, default_signal())
    betting = betting_scores.get(team, default_signal())
    off_field = off_field_signal(team)
    host_adjustment = 35.0 if team in HOST_TEAMS else 0.0
    ranking_adj = ranking_adjustment(rankings.get(team))
    rules_adj = rule_adaptation_adjustment(stat)
    components = {
        "elo": float(stat["elo"]),
        "form": float(stat.get("form_adjustment", 0.0)),
        "goldman": float(stat.get("goldman_adjustment", 0.0)),
        "market": float(market.get("adjustment", 0.0)),
        "betting": float(betting.get("adjustment", 0.0)),
        "off_field": float(off_field.get("adjustment", 0.0)),
        "rules": rules_adj,
        "host": host_adjustment,
        "ranking": ranking_adj,
    }
    rating = sum(components.values())
    return rating, components, stat, market, betting, off_field


def predict_match(
    match: Dict[str, Any],
    team_stats: Dict[str, Dict[str, Any]],
    market_scores: Dict[str, Dict[str, Any]],
    rankings: Optional[Dict[str, int]] = None,
    betting_scores: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    team1 = canonicalize_team(match["team1"], team_stats.keys())
    team2 = canonicalize_team(match["team2"], team_stats.keys())
    base = dict(match)
    base["team1"] = team1
    base["team2"] = team2
    if is_placeholder_team(team1) or is_placeholder_team(team2):
        base.update(
            {
                "teams_confirmed": False,
                "probabilities": None,
                "favorite": "待定",
                "predicted_score": "待定",
                "confidence": 0.0,
                "confidence_label": "待定",
                "explanation": ["参赛队尚未确定，暂不计算预测。"],
                "contributors": [],
                "team_metrics": {},
                "scoreline_distribution": [],
                "advance_probabilities": None,
            }
        )
        return base

    rankings = rankings or {}
    betting_scores = betting_scores or {}
    rating1, components1, stat1, market1, betting1, off_field1 = effective_team_rating(team1, team_stats, market_scores, betting_scores, rankings)
    rating2, components2, stat2, market2, betting2, off_field2 = effective_team_rating(team2, team_stats, market_scores, betting_scores, rankings)
    diff = rating1 - rating2

    lambda_base = 1.42
    lambda1 = clamp(
        lambda_base
        * stat1.get("goldman_attack", stat1["attack"])
        * stat2.get("goldman_defense", stat2["defense"])
        * math.exp(diff / 900.0)
        * context_attack_multiplier(components1)
        * context_defense_multiplier(components2),
        0.25,
        3.8,
    )
    lambda2 = clamp(
        lambda_base
        * stat2.get("goldman_attack", stat2["attack"])
        * stat1.get("goldman_defense", stat1["defense"])
        * math.exp(-diff / 900.0)
        * context_attack_multiplier(components2)
        * context_defense_multiplier(components1),
        0.25,
        3.8,
    )
    distribution, probabilities_raw = score_matrix(lambda1, lambda2)
    confidence, label = confidence_label(probabilities_raw)
    probabilities = {key: pct(value) for key, value in probabilities_raw.items()}
    favorite_key = max(probabilities_raw, key=probabilities_raw.get)
    if favorite_key == "draw":
        favorite = "平局倾向"
    elif favorite_key == "team1_win":
        favorite = team1
    else:
        favorite = team2

    shootout_bias = expected_score(rating1, rating2)
    advance_probabilities = None
    if match.get("is_knockout"):
        advance1 = probabilities_raw["team1_win"] + probabilities_raw["draw"] * shootout_bias
        advance2 = probabilities_raw["team2_win"] + probabilities_raw["draw"] * (1.0 - shootout_bias)
        total = advance1 + advance2
        advance_probabilities = {
            "team1": pct(advance1 / total if total else 0.5),
            "team2": pct(advance2 / total if total else 0.5),
            "note": "淘汰赛晋级倾向包含常规时间胜负和点球不确定性近似。",
        }

    top_scores = [
        {"score": item["score"], "probability": pct(item["probability"])}
        for item in distribution[:6]
    ]
    modal_score = top_scores[0]["score"] if top_scores else "待定"
    expected_total = lambda1 + lambda2
    predicted_score = select_representative_score(distribution, probabilities_raw, expected_total)
    score_summary = {
        "representative_score": predicted_score,
        "modal_score": modal_score,
        "expected_total_goals": round(expected_total, 2),
        **score_distribution_summary(distribution),
    }
    contributors = [
        {
            "name": "基础 Elo 差",
            "value": round(components1["elo"] - components2["elo"], 1),
            "description": f"{team1} 与 {team2} 的长期实力差。",
        },
        {
            "name": "近期状态差",
            "value": round(components1["form"] - components2["form"], 1),
            "description": "最近 10 场的积分率、净胜球和对手强度。",
        },
        {
            "name": "高盛式特征修正",
            "value": round(components1["goldman"] - components2["goldman"], 1),
            "description": "正式比赛近期攻防、世界杯正赛历史表现、阶段经验和主大陆因素。",
        },
        {
            "name": "世界杯阶段经验",
            "value": round(float(stat1.get("world_cup_stage_adjustment", 0.0)) - float(stat2.get("world_cup_stage_adjustment", 0.0)), 1),
            "description": "来自本地历届世界杯 CSV 的正赛阶段、淘汰赛和半决赛/决赛经验。",
        },
        {
            "name": "主办国修正",
            "value": round(components1["host"] - components2["host"], 1),
            "description": "美国、墨西哥、加拿大作为东道主的小幅修正。",
        },
        {
            "name": "市场热度修正",
            "value": round(components1["market"] - components2["market"], 1),
            "description": "义乌外贸、世界杯周边订单和公开页面提及度的辅助信号。",
        },
        {
            "name": "博彩盘口修正",
            "value": round(components1["betting"] - components2["betting"], 1),
            "description": "公开赔率对比页中的冠军赔率、盘口页面提及度和隐含概率。",
        },
        {
            "name": "场外不确定性修正",
            "value": round(components1["off_field"] - components2["off_field"], 1),
            "description": "装备、签证、入境、旅行和临时后勤事件，只作为小幅临场扰动。",
        },
        {
            "name": "新规则适应性",
            "value": round(components1["rules"] - components2["rules"], 1),
            "description": "补水暂停、门将持球限制、界外球/门球倒计时等规则下的攻防适应性。",
        },
        {
            "name": "FIFA 排名参考",
            "value": round(components1["ranking"] - components2["ranking"], 1),
            "description": "仅在公开页面可解析到足够排名时启用。",
        },
    ]
    explanation = [
        f"{team1} 有效评分 {rating1:.0f}，{team2} 有效评分 {rating2:.0f}。",
        f"模型预计进球均值为 {team1} {lambda1:.2f}，{team2} {lambda2:.2f}。",
        f"代表比分为 {predicted_score}，精确众数比分为 {modal_score}，预测置信度为{label}。",
    ]

    base.update(
        {
            "teams_confirmed": True,
            "probabilities": probabilities,
            "favorite": favorite,
            "predicted_score": predicted_score,
            "confidence": round(confidence, 3),
            "confidence_label": label,
            "expected_goals": {"team1": round(lambda1, 2), "team2": round(lambda2, 2)},
            "score_summary": score_summary,
            "effective_ratings": {"team1": round(rating1, 1), "team2": round(rating2, 1)},
            "market": {
                "team1": market1,
                "team2": market2,
                "available": bool(market1.get("available") or market2.get("available")),
            },
            "betting_market": {
                "team1": betting1,
                "team2": betting2,
                "available": bool(betting1.get("available") or betting2.get("available")),
            },
            "off_field": {
                "team1": off_field1,
                "team2": off_field2,
                "available": bool(off_field1.get("available") or off_field2.get("available")),
            },
            "rule_adaptation": {"team1": components1["rules"], "team2": components2["rules"]},
            "fifa_ranking": {"team1": rankings.get(team1), "team2": rankings.get(team2)},
            "contributors": contributors,
            "explanation": explanation,
            "team_metrics": {team1: stat1, team2: stat2},
            "scoreline_distribution": top_scores,
            "advance_probabilities": advance_probabilities,
        }
    )
    return base


def fallback_team_stat(team: str) -> Dict[str, Any]:
    return {
        "team": team,
        "elo": 1500.0,
        "matches": 0,
        "recent_points_rate": 0.5,
        "recent_goal_diff": 0.0,
        "recent_opponent_elo": 1500.0,
        "form_adjustment": 0.0,
        "attack": 1.0,
        "defense": 1.0,
        "competitive_points_rate": 0.5,
        "competitive_goal_diff": 0.0,
        "competitive_opponent_elo": 1500.0,
        "competitive_adjustment": 0.0,
        "world_cup_points_rate": 0.0,
        "world_cup_goal_diff": 0.0,
        "world_cup_adjustment": 0.0,
        "world_cup_stage_adjustment": 0.0,
        "world_cup_stage_points_rate": 0.0,
        "world_cup_stage_goal_diff": 0.0,
        "world_cup_local_matches": 0,
        "world_cup_knockout_matches": 0,
        "world_cup_knockout_win_rate": 0.0,
        "home_continent_adjustment": home_continent_adjustment(team),
        "goldman_adjustment": home_continent_adjustment(team),
        "mandatory_attack": 1.0,
        "mandatory_defense": 1.0,
        "goldman_attack": 1.0,
        "goldman_defense": 1.0,
    }


def match_summary(match: Dict[str, Any]) -> Dict[str, Any]:
    fields = [
        "id",
        "index",
        "round",
        "group",
        "stage",
        "date",
        "time",
        "starts_at",
        "team1",
        "team2",
        "ground",
        "status",
        "is_knockout",
        "teams_confirmed",
        "probabilities",
        "favorite",
        "predicted_score",
        "confidence",
        "confidence_label",
        "expected_goals",
        "advance_probabilities",
        "actual_score",
        "prediction_result",
        "off_field",
        "rule_adaptation",
    ]
    return {key: match.get(key) for key in fields}


def load_actual_results(path: Path = ACTUAL_RESULTS_FILE) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    results: Dict[str, Dict[str, Any]] = {}
    for item in parsed.get("results", []):
        match_id = item.get("match_id")
        if not match_id:
            continue
        goals1 = safe_int_value(item.get("team1_goals"))
        goals2 = safe_int_value(item.get("team2_goals"))
        if goals1 is None or goals2 is None:
            score = score_from_schedule_item(item)
            if not score:
                continue
            goals1 = score["team1"]
            goals2 = score["team2"]
        results[str(match_id)] = {
            "team1_name": item.get("team1"),
            "team2_name": item.get("team2"),
            "team1": goals1,
            "team2": goals2,
            "score": f"{goals1}-{goals2}",
            "source_name": item.get("source_name") or "公开赛果",
            "source_url": item.get("source_url") or "",
            "verified_at": item.get("verified_at") or parsed.get("updated_at"),
        }
    return results


def score_outcome(goals1: int, goals2: int) -> str:
    if goals1 > goals2:
        return "team1_win"
    if goals2 > goals1:
        return "team2_win"
    return "draw"


def predicted_outcome(match: Dict[str, Any]) -> Optional[str]:
    probabilities = match.get("probabilities") or {}
    if not probabilities:
        return None
    return max(("team1_win", "draw", "team2_win"), key=lambda key: float(probabilities.get(key) or 0.0))


def parse_scoreline(score: str) -> Optional[Tuple[int, int]]:
    match = re.search(r"(\d+)\s*-\s*(\d+)", score or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def apply_actual_results(matches: List[Dict[str, Any]], actual_results: Dict[str, Dict[str, Any]]) -> None:
    for match in matches:
        actual = match.get("actual_score") or actual_results.get(match.get("id"))
        if not actual:
            continue
        expected_team1 = actual.get("team1_name")
        expected_team2 = actual.get("team2_name")
        if expected_team1 and canonicalize_team(expected_team1) != canonicalize_team(match.get("team1", "")):
            continue
        if expected_team2 and canonicalize_team(expected_team2) != canonicalize_team(match.get("team2", "")):
            continue
        goals1 = safe_int_value(actual.get("team1"))
        goals2 = safe_int_value(actual.get("team2"))
        if goals1 is None or goals2 is None:
            continue

        actual_score = {
            "team1": goals1,
            "team2": goals2,
            "score": f"{goals1}-{goals2}",
            "source_name": actual.get("source_name") or "公开赛果",
            "source_url": actual.get("source_url") or "",
            "verified_at": actual.get("verified_at"),
        }
        actual_outcome = score_outcome(goals1, goals2)
        predicted = predicted_outcome(match)
        predicted_score = parse_scoreline(match.get("predicted_score", ""))
        exact_score_hit = bool(predicted_score and predicted_score == (goals1, goals2))
        goal_error = None
        if predicted_score:
            goal_error = abs(predicted_score[0] - goals1) + abs(predicted_score[1] - goals2)

        match["actual_score"] = actual_score
        match["prediction_result"] = {
            "actual_outcome": actual_outcome,
            "predicted_outcome": predicted,
            "outcome_hit": predicted == actual_outcome,
            "exact_score_hit": exact_score_hit,
            "goal_error": goal_error,
        }


def build_prediction_performance(matches: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    completed = [match for match in matches if match.get("actual_score") and match.get("prediction_result")]
    sample_size = len(completed)
    if not sample_size:
        return {
            "sample_size": 0,
            "outcome_hits": 0,
            "exact_score_hits": 0,
            "outcome_accuracy": None,
            "exact_score_accuracy": None,
            "average_goal_error": None,
            "completed_matches": [],
            "note": "暂无已接入真实赛果；有官方赛果后会自动生成模型预测能力对比。",
        }

    outcome_hits = sum(1 for match in completed if match["prediction_result"].get("outcome_hit"))
    exact_score_hits = sum(1 for match in completed if match["prediction_result"].get("exact_score_hit"))
    goal_errors = [
        float(match["prediction_result"]["goal_error"])
        for match in completed
        if match["prediction_result"].get("goal_error") is not None
    ]
    rows = []
    for match in completed:
        actual = match["actual_score"]
        result = match["prediction_result"]
        rows.append(
            {
                "id": match.get("id"),
                "date": match.get("date"),
                "team1": match.get("team1"),
                "team2": match.get("team2"),
                "predicted_score": match.get("predicted_score"),
                "actual_score": actual.get("score"),
                "outcome_hit": result.get("outcome_hit"),
                "exact_score_hit": result.get("exact_score_hit"),
                "goal_error": result.get("goal_error"),
                "source_name": actual.get("source_name"),
                "source_url": actual.get("source_url"),
            }
        )
    return {
        "sample_size": sample_size,
        "outcome_hits": outcome_hits,
        "exact_score_hits": exact_score_hits,
        "outcome_accuracy": pct(outcome_hits / sample_size),
        "exact_score_accuracy": pct(exact_score_hits / sample_size),
        "average_goal_error": round(sum(goal_errors) / len(goal_errors), 2) if goal_errors else None,
        "completed_matches": rows,
        "note": "早期样本较小，命中率会随更多真实赛果持续更新。",
    }


def group_letter(group_name: str) -> Optional[str]:
    match = re.search(r"Group\s+([A-L])", group_name or "", re.IGNORECASE)
    return match.group(1).upper() if match else None


def stage_key(round_name: str) -> str:
    text = (round_name or "").lower()
    if "round of 32" in text:
        return "round_of_32"
    if "round of 16" in text:
        return "round_of_16"
    if "quarter" in text:
        return "quarter_final"
    if "semi" in text:
        return "semi_final"
    if "third" in text:
        return "third_place"
    if "final" in text:
        return "final"
    return "knockout"


def stage_label(key: str) -> str:
    labels = {
        "round_of_32": "32强",
        "round_of_16": "16强",
        "quarter_final": "8强",
        "semi_final": "4强 / 半决赛",
        "final": "决赛",
        "champion": "冠军",
        "third_place": "三四名决赛",
    }
    return labels.get(key, key)


def build_matchup_rounds(
    projected_matches: Sequence[Dict[str, Any]],
    predicted_stages: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    stage_team_map = {stage["key"]: stage.get("teams", []) for stage in predicted_stages}
    match_stage_defs = [
        ("round_of_32", "32强对阵"),
        ("round_of_16", "16强对阵"),
        ("quarter_final", "8强对阵"),
        ("semi_final", "半决赛对阵"),
        ("final", "决赛对阵"),
    ]
    rounds: List[Dict[str, Any]] = [
        {
            "key": "semi_finalists",
            "label": "4强名单",
            "type": "teams",
            "teams": stage_team_map.get("semi_final", []),
        }
    ]
    for key, label in match_stage_defs:
        matches = [
            {
                "id": match.get("id"),
                "index": match.get("index"),
                "team1": match.get("team1"),
                "team2": match.get("team2"),
                "winner": match.get("winner"),
                "predicted_score": match.get("predicted_score"),
                "confidence_label": match.get("confidence_label"),
                "ground": match.get("ground"),
                "starts_at": match.get("starts_at"),
            }
            for match in projected_matches
            if match.get("stage_key") == key
        ]
        rounds.append({"key": key, "label": label, "type": "matches", "matches": matches})
    order = ["round_of_32", "round_of_16", "quarter_final", "semi_finalists", "semi_final", "final"]
    return sorted(rounds, key=lambda item: order.index(item["key"]) if item["key"] in order else len(order))


def probability_to_float(probabilities: Optional[Dict[str, float]], key: str) -> float:
    if not probabilities:
        return 0.0
    return float(probabilities.get(key, 0.0)) / 100.0


def poisson_sample(rng: random.Random, lam: float) -> int:
    lam = clamp(lam, 0.05, 6.0)
    threshold = math.exp(-lam)
    product = 1.0
    goals = 0
    while product > threshold and goals < 10:
        goals += 1
        product *= rng.random()
    return goals - 1


def table_row(team: str) -> Dict[str, Any]:
    return {"team": team, "points": 0.0, "gf": 0.0, "ga": 0.0, "gd": 0.0}


def add_result(row: Dict[str, Any], points: float, gf: float, ga: float) -> None:
    row["points"] += points
    row["gf"] += gf
    row["ga"] += ga
    row["gd"] = row["gf"] - row["ga"]


def actual_goals(match: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    actual = match.get("actual_score") or {}
    goals1 = safe_int_value(actual.get("team1"))
    goals2 = safe_int_value(actual.get("team2"))
    if goals1 is None or goals2 is None:
        return None
    return goals1, goals2


def points_from_goals(goals1: int, goals2: int) -> Tuple[float, float]:
    if goals1 > goals2:
        return 3.0, 0.0
    if goals2 > goals1:
        return 0.0, 3.0
    return 1.0, 1.0


def rank_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: (-row["points"], -row["gd"], -row["gf"], row["team"]))
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row["points"] = round(row["points"], 2)
        row["gf"] = round(row["gf"], 2)
        row["ga"] = round(row["ga"], 2)
        row["gd"] = round(row["gd"], 2)
    return ranked


def expected_group_tables(matches: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    tables: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for match in matches:
        group = group_letter(match.get("group", ""))
        if not group or not match.get("teams_confirmed"):
            continue
        table = tables[group]
        team1, team2 = match["team1"], match["team2"]
        table.setdefault(team1, table_row(team1))
        table.setdefault(team2, table_row(team2))
        actual = actual_goals(match)
        if actual:
            goals1, goals2 = actual
            points1, points2 = points_from_goals(goals1, goals2)
            add_result(table[team1], points1, goals1, goals2)
            add_result(table[team2], points2, goals2, goals1)
            continue
        p1 = probability_to_float(match.get("probabilities"), "team1_win")
        draw = probability_to_float(match.get("probabilities"), "draw")
        p2 = probability_to_float(match.get("probabilities"), "team2_win")
        eg1 = (match.get("expected_goals") or {}).get("team1", 1.2)
        eg2 = (match.get("expected_goals") or {}).get("team2", 1.2)
        add_result(table[team1], p1 * 3.0 + draw, eg1, eg2)
        add_result(table[team2], p2 * 3.0 + draw, eg2, eg1)
    return {group: rank_rows(table.values()) for group, table in sorted(tables.items())}


def simulate_group_tables(matches: Sequence[Dict[str, Any]], rng: random.Random) -> Dict[str, List[Dict[str, Any]]]:
    tables: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for match in matches:
        group = group_letter(match.get("group", ""))
        if not group or not match.get("teams_confirmed"):
            continue
        table = tables[group]
        team1, team2 = match["team1"], match["team2"]
        table.setdefault(team1, table_row(team1))
        table.setdefault(team2, table_row(team2))
        actual = actual_goals(match)
        if actual:
            goals1, goals2 = actual
            points1, points2 = points_from_goals(goals1, goals2)
            add_result(table[team1], points1, goals1, goals2)
            add_result(table[team2], points2, goals2, goals1)
            continue
        p1 = probability_to_float(match.get("probabilities"), "team1_win")
        draw = probability_to_float(match.get("probabilities"), "draw")
        roll = rng.random()
        outcome = "team1_win" if roll < p1 else "draw" if roll < p1 + draw else "team2_win"
        expected_goals = match.get("expected_goals") or {}
        goals1 = poisson_sample(rng, expected_goals.get("team1", 1.2))
        goals2 = poisson_sample(rng, expected_goals.get("team2", 1.2))
        if outcome == "team1_win" and goals1 <= goals2:
            goals1 = goals2 + 1
        elif outcome == "team2_win" and goals2 <= goals1:
            goals2 = goals1 + 1
        elif outcome == "draw":
            draw_goals = int(round((goals1 + goals2) / 2.0))
            goals1 = draw_goals
            goals2 = draw_goals

        if goals1 > goals2:
            points1, points2 = 3.0, 0.0
        elif goals1 == goals2:
            points1, points2 = 1.0, 1.0
        else:
            points1, points2 = 0.0, 3.0
        add_result(table[team1], points1, goals1, goals2)
        add_result(table[team2], points2, goals2, goals1)
    return {group: rank_rows(table.values()) for group, table in sorted(tables.items())}


def qualified_from_tables(tables: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[str], Dict[str, str], Dict[str, List[Dict[str, Any]]]]:
    qualified: List[str] = []
    position_map: Dict[str, str] = {}
    thirds: List[Dict[str, Any]] = []
    for group in GROUP_LETTERS:
        rows = tables.get(group, [])
        if len(rows) < 3:
            continue
        first, second, third = rows[0], rows[1], rows[2]
        position_map[f"1{group}"] = first["team"]
        position_map[f"2{group}"] = second["team"]
        qualified.extend([first["team"], second["team"]])
        thirds.append({**third, "group": group})
    best_thirds = rank_rows(thirds)[:8]
    third_map: Dict[str, List[Dict[str, Any]]] = {}
    for row in best_thirds:
        position_map[f"3{row['group']}"] = row["team"]
        qualified.append(row["team"])
        third_map[row["group"]] = [row]
    return qualified, position_map, third_map


def resolve_slot(
    slot: str,
    position_map: Dict[str, str],
    winners: Dict[int, str],
    losers: Dict[int, str],
    used_third_groups: set,
) -> Optional[str]:
    slot = (slot or "").strip()
    upper = slot.upper()
    if upper in position_map:
        return position_map[upper]
    if re.fullmatch(r"3[A-L](?:/[A-L])+", upper):
        allowed = upper[1:].split("/")
        for group in allowed:
            key = f"3{group}"
            if key in position_map and group not in used_third_groups:
                used_third_groups.add(group)
                return position_map[key]
        for group in allowed:
            key = f"3{group}"
            if key in position_map:
                return position_map[key]
        return None
    match = re.fullmatch(r"W(\d{2,3})", upper)
    if match:
        return winners.get(int(match.group(1)))
    match = re.fullmatch(r"L(\d{2,3})", upper)
    if match:
        return losers.get(int(match.group(1)))
    if is_placeholder_team(slot):
        return None
    return canonicalize_team(slot)


def virtual_prediction(
    team1: str,
    team2: str,
    team_stats: Dict[str, Dict[str, Any]],
    market_scores: Dict[str, Dict[str, Any]],
    betting_scores: Dict[str, Dict[str, Any]],
    rankings: Dict[str, int],
    match: Dict[str, Any],
) -> Dict[str, Any]:
    virtual_match = dict(match)
    virtual_match["team1"] = team1
    virtual_match["team2"] = team2
    virtual_match["group"] = ""
    virtual_match["is_knockout"] = True
    return predict_match(virtual_match, team_stats, market_scores, rankings, betting_scores)


def deterministic_bracket_projection(
    matches: Sequence[Dict[str, Any]],
    team_stats: Dict[str, Dict[str, Any]],
    market_scores: Dict[str, Dict[str, Any]],
    betting_scores: Dict[str, Dict[str, Any]],
    rankings: Dict[str, int],
) -> Dict[str, Any]:
    group_matches = [match for match in matches if group_letter(match.get("group", ""))]
    knockout_matches = [match for match in matches if match.get("is_knockout")]
    tables = expected_group_tables(group_matches)
    qualified, position_map, _ = qualified_from_tables(tables)
    winners: Dict[int, str] = {}
    losers: Dict[int, str] = {}
    used_third_groups: set = set()
    projected_matches: List[Dict[str, Any]] = []
    stage_teams: Dict[str, List[str]] = {
        "round_of_32": qualified,
        "round_of_16": [],
        "quarter_final": [],
        "semi_final": [],
        "final": [],
        "champion": [],
    }

    for match in sorted(knockout_matches, key=lambda item: item["index"]):
        team1 = resolve_slot(match["team1"], position_map, winners, losers, used_third_groups)
        team2 = resolve_slot(match["team2"], position_map, winners, losers, used_third_groups)
        current_stage = stage_key(match.get("round", ""))
        if not team1 or not team2:
            projected_matches.append({**match, "team1": team1 or match["team1"], "team2": team2 or match["team2"], "winner": "待定"})
            continue
        prediction = virtual_prediction(team1, team2, team_stats, market_scores, betting_scores, rankings, match)
        advance = prediction.get("advance_probabilities") or {"team1": 50.0, "team2": 50.0}
        if float(advance["team1"]) >= float(advance["team2"]):
            winner, loser = team1, team2
        else:
            winner, loser = team2, team1
        winners[match["index"]] = winner
        losers[match["index"]] = loser
        if current_stage == "round_of_32":
            stage_teams["round_of_16"].append(winner)
        elif current_stage == "round_of_16":
            stage_teams["quarter_final"].append(winner)
        elif current_stage == "quarter_final":
            stage_teams["semi_final"].append(winner)
        elif current_stage == "semi_final":
            stage_teams["final"].append(winner)
        elif current_stage == "final":
            stage_teams["champion"].append(winner)
        projected_matches.append(
            {
                "id": match["id"],
                "index": match["index"],
                "round": match["round"],
                "stage_key": current_stage,
                "stage_label": stage_label(current_stage),
                "date": match["date"],
                "starts_at": match["starts_at"],
                "ground": match["ground"],
                "team1": team1,
                "team2": team2,
                "winner": winner,
                "predicted_score": prediction.get("predicted_score"),
                "confidence_label": prediction.get("confidence_label"),
                "advance_probabilities": advance,
            }
        )

    predicted_stages = [
        {"key": key, "label": stage_label(key), "teams": teams}
        for key, teams in stage_teams.items()
    ]
    matchup_rounds = build_matchup_rounds(projected_matches, predicted_stages)
    group_tables = [
        {"group": f"Group {group}", "rows": rows}
        for group, rows in tables.items()
    ]
    return {
        "predicted_stages": predicted_stages,
        "projected_matches": projected_matches,
        "matchup_rounds": matchup_rounds,
        "group_tables": group_tables,
    }


def simulated_stage_probabilities(
    matches: Sequence[Dict[str, Any]],
    teams: Sequence[str],
    team_stats: Dict[str, Dict[str, Any]],
    market_scores: Dict[str, Dict[str, Any]],
    betting_scores: Dict[str, Dict[str, Any]],
    rankings: Dict[str, int],
    simulations: int = TOURNAMENT_SIMULATIONS,
) -> List[Dict[str, Any]]:
    group_inputs: List[Tuple[str, str, str, float, float, float, float, Optional[int], Optional[int]]] = []
    group_teams: Dict[str, set] = defaultdict(set)
    for match in matches:
        group = group_letter(match.get("group", ""))
        if not group or not match.get("teams_confirmed"):
            continue
        team1, team2 = match["team1"], match["team2"]
        expected_goals = match.get("expected_goals") or {}
        actual = actual_goals(match)
        actual1, actual2 = actual if actual else (None, None)
        group_inputs.append(
            (
                group,
                team1,
                team2,
                probability_to_float(match.get("probabilities"), "team1_win"),
                probability_to_float(match.get("probabilities"), "draw"),
                float(expected_goals.get("team1", 1.2)),
                float(expected_goals.get("team2", 1.2)),
                actual1,
                actual2,
            )
        )
        group_teams[group].update([team1, team2])
    knockout_matches = sorted([match for match in matches if match.get("is_knockout")], key=lambda item: item["index"])
    counts: Dict[str, Counter[str]] = {
        "round_of_32": Counter(),
        "round_of_16": Counter(),
        "quarter_final": Counter(),
        "semi_final": Counter(),
        "final": Counter(),
        "champion": Counter(),
    }
    rng = random.Random(TOURNAMENT_RANDOM_SEED)
    advance_cache: Dict[Tuple[str, str], float] = {}

    def fast_advance_probability(team1: str, team2: str) -> float:
        key = (team1, team2)
        if key in advance_cache:
            return advance_cache[key]
        rating1, _, _, _, _, _ = effective_team_rating(team1, team_stats, market_scores, betting_scores, rankings)
        rating2, _, _, _, _, _ = effective_team_rating(team2, team_stats, market_scores, betting_scores, rankings)
        probability = clamp(expected_score(rating1, rating2), 0.06, 0.94)
        advance_cache[key] = probability
        advance_cache[(team2, team1)] = 1.0 - probability
        return probability

    def simulated_positions() -> Tuple[List[str], Dict[str, str]]:
        tables: Dict[str, Dict[str, List[float]]] = {
            group: {team: [0.0, 0.0, 0.0] for team in teams_in_group}
            for group, teams_in_group in group_teams.items()
        }
        for group, team1, team2, p1, draw, eg1, eg2, actual1, actual2 in group_inputs:
            if actual1 is not None and actual2 is not None:
                goals1, goals2 = actual1, actual2
                pts1, pts2 = points_from_goals(goals1, goals2)
                row1 = tables[group][team1]
                row2 = tables[group][team2]
                row1[0] += pts1
                row1[1] += goals1
                row1[2] += goals2
                row2[0] += pts2
                row2[1] += goals2
                row2[2] += goals1
                continue
            roll = rng.random()
            goals1 = poisson_sample(rng, eg1)
            goals2 = poisson_sample(rng, eg2)
            if roll < p1:
                if goals1 <= goals2:
                    goals1 = goals2 + 1
                pts1, pts2 = 3.0, 0.0
            elif roll < p1 + draw:
                draw_goals = int(round((goals1 + goals2) / 2.0))
                goals1 = draw_goals
                goals2 = draw_goals
                pts1, pts2 = 1.0, 1.0
            else:
                if goals2 <= goals1:
                    goals2 = goals1 + 1
                pts1, pts2 = 0.0, 3.0
            row1 = tables[group][team1]
            row2 = tables[group][team2]
            row1[0] += pts1
            row1[1] += goals1
            row1[2] += goals2
            row2[0] += pts2
            row2[1] += goals2
            row2[2] += goals1

        qualified: List[str] = []
        position_map: Dict[str, str] = {}
        thirds: List[Tuple[str, str, float, float, float, float]] = []
        for group in GROUP_LETTERS:
            table = tables.get(group)
            if not table:
                continue
            ranked = sorted(
                (
                    (team, values[0], values[1], values[2], values[1] - values[2])
                    for team, values in table.items()
                ),
                key=lambda row: (-row[1], -row[4], -row[2], row[0]),
            )
            if len(ranked) < 3:
                continue
            first, second, third = ranked[0], ranked[1], ranked[2]
            position_map[f"1{group}"] = first[0]
            position_map[f"2{group}"] = second[0]
            qualified.extend([first[0], second[0]])
            thirds.append((group, third[0], third[1], third[2], third[3], third[4]))
        best_thirds = sorted(thirds, key=lambda row: (-row[2], -row[5], -row[3], row[1]))[:8]
        for group, team, *_ in best_thirds:
            position_map[f"3{group}"] = team
            qualified.append(team)
        return qualified, position_map

    for _ in range(simulations):
        qualified, position_map = simulated_positions()
        counts["round_of_32"].update(qualified)
        winners: Dict[int, str] = {}
        losers: Dict[int, str] = {}
        used_third_groups: set = set()
        for match in knockout_matches:
            team1 = resolve_slot(match["team1"], position_map, winners, losers, used_third_groups)
            team2 = resolve_slot(match["team2"], position_map, winners, losers, used_third_groups)
            if not team1 or not team2:
                continue
            if rng.random() < fast_advance_probability(team1, team2):
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1
            winners[match["index"]] = winner
            losers[match["index"]] = loser
            current_stage = stage_key(match.get("round", ""))
            if current_stage == "round_of_32":
                counts["round_of_16"][winner] += 1
            elif current_stage == "round_of_16":
                counts["quarter_final"][winner] += 1
            elif current_stage == "quarter_final":
                counts["semi_final"][winner] += 1
            elif current_stage == "semi_final":
                counts["final"][winner] += 1
            elif current_stage == "final":
                counts["champion"][winner] += 1

    rows: List[Dict[str, Any]] = []
    for team in teams:
        rows.append(
            {
                "team": team,
                "round_of_32": pct(counts["round_of_32"][team] / simulations),
                "round_of_16": pct(counts["round_of_16"][team] / simulations),
                "quarter_final": pct(counts["quarter_final"][team] / simulations),
                "semi_final": pct(counts["semi_final"][team] / simulations),
                "final": pct(counts["final"][team] / simulations),
                "champion": pct(counts["champion"][team] / simulations),
            }
        )
    rows.sort(key=lambda row: (-row["champion"], -row["final"], -row["semi_final"], row["team"]))
    return rows


def build_tournament_projection(
    matches: Sequence[Dict[str, Any]],
    teams: Sequence[str],
    team_stats: Dict[str, Dict[str, Any]],
    market_scores: Dict[str, Dict[str, Any]],
    betting_scores: Dict[str, Dict[str, Any]],
    rankings: Dict[str, int],
) -> Dict[str, Any]:
    deterministic = deterministic_bracket_projection(matches, team_stats, market_scores, betting_scores, rankings)
    probabilities = simulated_stage_probabilities(matches, teams, team_stats, market_scores, betting_scores, rankings)
    return {
        "simulations": TOURNAMENT_SIMULATIONS,
        "stage_probabilities": probabilities,
        "predicted_stages": deterministic["predicted_stages"],
        "projected_matches": deterministic["projected_matches"],
        "matchup_rounds": deterministic["matchup_rounds"],
        "group_tables": deterministic["group_tables"],
        "notes": [
            "32强概率来自小组赛和淘汰赛路径模拟。",
            "模型参考高盛公开思路，加入 Elo、正式比赛近期攻防、世界杯正赛历史、主办国/主大陆和赔率市场信号。",
            "冠军赔率只作为市场盘口辅助信号，不构成投注建议。",
        ],
    }


def build_predictions(raw_payloads: Dict[str, str], source_statuses: List[Dict[str, object]]) -> Dict[str, Any]:
    missing_required = []
    if not raw_payloads.get("schedule_openfootball"):
        missing_required.append("赛程")
    if not raw_payloads.get("results_history"):
        missing_required.append("历史比赛")
    if missing_required:
        raise ValueError("缺少必要数据源：" + "、".join(missing_required))

    schedule = parse_schedule(raw_payloads["schedule_openfootball"])
    schedule_teams = sorted(
        {
            canonicalize_team(team)
            for match in schedule
            for team in (match["team1"], match["team2"])
            if team and not is_placeholder_team(team)
        }
    )
    base_results = parse_results_csv(raw_payloads["results_history"], schedule_teams)
    world_cup_results = parse_world_cup_matches_csv(raw_payloads.get("worldcup_matches_local", ""), schedule_teams)
    results = merge_results(base_results, world_cup_results)
    world_cup_profiles = build_world_cup_profiles(world_cup_results, schedule_teams)
    team_stats = build_team_stats(results, schedule_teams, world_cup_profiles)

    market_source_ids = ["yiwu_index", "mofcom_forecast", "chinagoods", "yiwu_worldcup_search"]
    market_texts = [raw_payloads.get(source_id, "") for source_id in market_source_ids]
    market_scores = build_market_scores(schedule_teams, market_texts)
    betting_texts = [raw_payloads.get(source_id, "") for source_id in BETTING_SOURCE_IDS]
    betting_scores = build_betting_scores(schedule_teams, betting_texts)
    rankings = parse_fifa_rankings(raw_payloads.get("fifa_ranking", ""), schedule_teams)

    matches = [predict_match(match, team_stats, market_scores, rankings, betting_scores) for match in schedule]
    apply_actual_results(matches, load_actual_results())
    performance = build_prediction_performance(matches)
    tournament = build_tournament_projection(matches, schedule_teams, team_stats, market_scores, betting_scores, rankings)
    filters = {
        "rounds": sorted({match["round"] for match in matches if match.get("round")}),
        "teams": schedule_teams,
        "statuses": sorted({match["status"] for match in matches if match.get("status")}),
        "confidence_levels": ["高", "中", "低", "待定"],
    }
    market_available = any(item.get("available") for item in market_scores.values())
    betting_available = any(item.get("available") for item in betting_scores.values())
    return {
        "model_version": MODEL_VERSION,
        "generated_at": now_iso(),
        "sources": source_statuses,
        "matches": matches,
        "tournament": tournament,
        "performance": performance,
        "filters": filters,
        "teams": {team: team_stats.get(team, fallback_team_stat(team)) for team in schedule_teams},
        "summary": {
            "match_count": len(matches),
            "team_count": len(schedule_teams),
            "result_rows": len(results),
            "world_cup_rows": len(world_cup_results),
            "world_cup_local_signal_available": bool(world_cup_results),
            "market_signal_available": market_available,
            "betting_signal_available": betting_available,
            "tournament_simulations": tournament["simulations"],
            "fifa_rankings_used": len(rankings),
            "actual_result_count": performance["sample_size"],
            "outcome_accuracy": performance["outcome_accuracy"],
            "exact_score_accuracy": performance["exact_score_accuracy"],
        },
        "error": None,
    }
