from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .cache import now_iso
from .model import apply_actual_results, build_prediction_performance, canonicalize_team, match_status


ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
SOURCE_ID = "espn_live_results"
SOURCE_NAME = "ESPN 世界杯实时比分"
TOURNAMENT_START = date(2026, 6, 11)


def sync_live_results(cache: Dict[str, Any]) -> Dict[str, Any]:
    payload = deepcopy(cache)
    matches = payload.get("matches") or []
    events, status = fetch_espn_completed_events()
    actual_results = build_actual_results(matches, events)

    for match in matches:
        match["status"] = match_status(match.get("starts_at"))

    apply_actual_results(matches, actual_results)
    performance = build_prediction_performance(matches)
    payload["matches"] = matches
    payload["performance"] = performance
    payload["generated_at"] = now_iso()
    payload["error"] = None

    summary = payload.setdefault("summary", {})
    summary["actual_result_count"] = performance["sample_size"]
    summary["outcome_accuracy"] = performance["outcome_accuracy"]
    summary["exact_score_accuracy"] = performance["exact_score_accuracy"]
    summary["finished_match_count"] = sum(1 for match in matches if match.get("status") == "已结束")
    summary["live_result_synced_at"] = payload["generated_at"]

    status["message"] = f"已同步 {len(actual_results)} 场已完赛比分"
    payload["sources"] = upsert_source(payload.get("sources") or [], status)
    return payload


def fetch_espn_completed_events() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    fetched_bytes = 0
    last_url = ESPN_SCOREBOARD_URL
    today = datetime.now(timezone.utc).date() + timedelta(days=1)
    days = max(0, min((today - TOURNAMENT_START).days, 80))

    with httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": "worldcup-predictor/1.0"}) as client:
        for offset in range(days + 1):
            current = TOURNAMENT_START + timedelta(days=offset)
            params = {"dates": current.strftime("%Y%m%d")}
            response = client.get(ESPN_SCOREBOARD_URL, params=params)
            last_url = str(response.url)
            response.raise_for_status()
            fetched_bytes += len(response.content)
            data = response.json()
            for raw_event in data.get("events") or []:
                parsed = parse_espn_event(raw_event, last_url)
                if parsed:
                    events.append(parsed)

    return events, {
        "id": SOURCE_ID,
        "name": SOURCE_NAME,
        "url": last_url,
        "ok": True,
        "using_cache": False,
        "fetched_at": now_iso(),
        "bytes": fetched_bytes,
        "message": "",
    }


def parse_espn_event(event: Dict[str, Any], source_url: str) -> Optional[Dict[str, Any]]:
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competition = competitions[0]
    status = (competition.get("status") or event.get("status") or {}).get("type") or {}
    if not status.get("completed"):
        return None

    competitors = competition.get("competitors") or []
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    home_score = safe_score(home.get("score"))
    away_score = safe_score(away.get("score"))
    if home_score is None or away_score is None:
        return None

    return {
        "home": team_name(home),
        "away": team_name(away),
        "home_score": home_score,
        "away_score": away_score,
        "date": event.get("date") or competition.get("date"),
        "source_url": source_url,
    }


def build_actual_results(matches: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    actual_results: Dict[str, Dict[str, Any]] = {}
    known_teams = sorted(
        {
            team
            for match in matches
            for team in (match.get("team1"), match.get("team2"))
            if team
        }
    )
    for event in events:
        matched = match_event(matches, event, known_teams)
        if not matched:
            continue
        match, team1_goals, team2_goals = matched
        actual_results[str(match["id"])] = {
            "team1_name": match.get("team1"),
            "team2_name": match.get("team2"),
            "team1": team1_goals,
            "team2": team2_goals,
            "score": f"{team1_goals}-{team2_goals}",
            "source_name": SOURCE_NAME,
            "source_url": event.get("source_url") or ESPN_SCOREBOARD_URL,
            "verified_at": now_iso(),
        }
    return actual_results


def match_event(
    matches: List[Dict[str, Any]], event: Dict[str, Any], known_teams: List[str]
) -> Optional[Tuple[Dict[str, Any], int, int]]:
    home = canonicalize_team(event.get("home", ""), known_teams)
    away = canonicalize_team(event.get("away", ""), known_teams)
    if not home or not away:
        return None

    event_time = parse_datetime(event.get("date"))
    candidates: List[Tuple[float, Dict[str, Any]]] = []
    for match in matches:
        team1 = canonicalize_team(match.get("team1", ""), known_teams)
        team2 = canonicalize_team(match.get("team2", ""), known_teams)
        if {team1, team2} != {home, away}:
            continue
        match_time = parse_datetime(match.get("starts_at"))
        delta = abs((match_time - event_time).total_seconds()) if match_time and event_time else 0
        candidates.append((delta, match))

    if not candidates:
        return None

    _, match = min(candidates, key=lambda item: item[0])
    team1 = canonicalize_team(match.get("team1", ""), known_teams)
    if team1 == home:
        return match, int(event["home_score"]), int(event["away_score"])
    return match, int(event["away_score"]), int(event["home_score"])


def upsert_source(sources: List[Dict[str, Any]], source: Dict[str, Any]) -> List[Dict[str, Any]]:
    kept = [item for item in sources if item.get("id") != SOURCE_ID]
    return [source, *kept]


def safe_score(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def team_name(competitor: Dict[str, Any]) -> str:
    team = competitor.get("team") or {}
    return team.get("displayName") or team.get("name") or competitor.get("displayName") or ""


def parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
