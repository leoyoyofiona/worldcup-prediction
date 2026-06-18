from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .cache import now_iso
from .config import MODEL_VERSION
from .model import (
    apply_actual_results,
    apply_post_match_calibration,
    apply_technical_calibration,
    build_technical_profiles,
    build_prediction_performance,
    build_post_match_calibration,
    build_tournament_projection,
    canonicalize_team,
    match_status,
)


ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"
SOURCE_ID = "espn_live_results"
SOURCE_NAME = "ESPN 世界杯实时比分/技术统计"
TOURNAMENT_START = date(2026, 6, 11)
TECHNICAL_STAT_MAP = {
    "possessionPct": "possession_pct",
    "totalShots": "shots",
    "shotsOnTarget": "shots_on_target",
    "wonCorners": "corners",
    "totalTackles": "tackles",
    "effectiveTackles": "effective_tackles",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "foulsCommitted": "fouls",
    "offsides": "offsides",
    "saves": "saves",
    "blockedShots": "blocked_shots",
    "interceptions": "interceptions",
    "totalPasses": "passes",
    "accuratePasses": "accurate_passes",
}


def sync_live_results(cache: Dict[str, Any]) -> Dict[str, Any]:
    payload = deepcopy(cache)
    matches = payload.get("matches") or []
    events, status = fetch_espn_completed_events()
    actual_results = build_actual_results(matches, events)
    technical_results = build_technical_results(matches, events)

    for match in matches:
        match["status"] = match_status(match.get("starts_at"))
        technical = technical_results.get(str(match.get("id")))
        if technical:
            match["technical_stats"] = technical

    apply_actual_results(matches, actual_results)
    performance = build_prediction_performance(matches)
    post_match_calibration = build_post_match_calibration(matches)
    apply_post_match_calibration(matches, post_match_calibration)
    technical_profiles = build_technical_profiles(matches)
    apply_technical_calibration(matches, technical_profiles)
    rebuild_tournament(payload, matches)
    payload["matches"] = matches
    payload["performance"] = performance
    payload["post_match_calibration"] = post_match_calibration
    payload["model_version"] = MODEL_VERSION
    payload["generated_at"] = now_iso()
    payload["error"] = None

    summary = payload.setdefault("summary", {})
    summary["actual_result_count"] = performance["sample_size"]
    summary["outcome_accuracy"] = performance["outcome_accuracy"]
    summary["exact_score_accuracy"] = performance["exact_score_accuracy"]
    summary["finished_match_count"] = sum(1 for match in matches if match.get("status") == "已结束")
    summary["post_match_calibration_available"] = post_match_calibration.get("available", False)
    summary["post_match_calibration_sample_size"] = post_match_calibration.get("sample_size", 0)
    summary["technical_stat_match_count"] = len(technical_results)
    summary["technical_stat_team_count"] = len(technical_profiles)
    summary["live_result_synced_at"] = payload["generated_at"]
    summary["tournament_synced_at"] = payload["generated_at"]

    status["message"] = f"已同步 {len(actual_results)} 场已完赛比分，{len(technical_results)} 场技术统计"
    payload["sources"] = upsert_source(payload.get("sources") or [], status)
    return payload


def rebuild_tournament(payload: Dict[str, Any], matches: List[Dict[str, Any]]) -> None:
    teams = payload.get("filters", {}).get("teams") or sorted(payload.get("teams", {}).keys())
    team_stats = payload.get("teams") or {}
    if not teams or not team_stats:
        return
    market_scores = collect_signal_scores(matches, "market")
    betting_scores = collect_signal_scores(matches, "betting_market")
    context_scores = collect_signal_scores(matches, "match_context")
    rankings = collect_rankings(matches)
    payload["tournament"] = build_tournament_projection(
        matches,
        teams,
        team_stats,
        market_scores,
        betting_scores,
        rankings,
        context_scores,
    )


def collect_signal_scores(matches: List[Dict[str, Any]], field: str) -> Dict[str, Dict[str, Any]]:
    scores: Dict[str, Dict[str, Any]] = {}
    for match in matches:
        signal = match.get(field) or {}
        for side in ("team1", "team2"):
            team = match.get(side)
            if team and side in signal and team not in scores:
                scores[team] = signal[side]
    return scores


def collect_rankings(matches: List[Dict[str, Any]]) -> Dict[str, int]:
    rankings: Dict[str, int] = {}
    for match in matches:
        ranking = match.get("fifa_ranking") or {}
        for side in ("team1", "team2"):
            value = ranking.get(side)
            team = match.get(side)
            if team and isinstance(value, int):
                rankings[team] = value
    return rankings


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
                summary = fetch_espn_summary(client, raw_event)
                technical = parse_espn_technical_event(raw_event, last_url, summary)
                parsed = parse_espn_event(raw_event, last_url)
                if parsed:
                    if technical:
                        parsed["technical_stats"] = technical.get("technical_stats")
                        parsed["technical_source_url"] = technical.get("technical_source_url")
                    events.append(parsed)
                elif technical:
                    events.append(technical)

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


def fetch_espn_summary(client: httpx.Client, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event_id = event.get("id")
    competitions = event.get("competitions") or []
    status = ((competitions[0].get("status") if competitions else {}) or event.get("status") or {}).get("type") or {}
    if not event_id or status.get("state") == "pre":
        return None
    try:
        response = client.get(ESPN_SUMMARY_URL, params={"event": event_id}, timeout=8.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


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


def parse_espn_technical_event(event: Dict[str, Any], source_url: str, summary: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competition = competitions[0]
    competitors = competition.get("competitors") or []
    home = next((item for item in competitors if item.get("homeAway") == "home"), None)
    away = next((item for item in competitors if item.get("homeAway") == "away"), None)
    if not home or not away:
        return None

    home_name = team_name(home)
    away_name = team_name(away)
    by_team = technical_stats_from_summary(summary) if summary else {}
    home_stats = by_team.get(home_name) or normalize_technical_stats(home.get("statistics") or [])
    away_stats = by_team.get(away_name) or normalize_technical_stats(away.get("statistics") or [])

    substitutions = substitution_counts(summary)
    if home_name in substitutions:
        home_stats["substitutions"] = substitutions[home_name]
    if away_name in substitutions:
        away_stats["substitutions"] = substitutions[away_name]
    if not has_technical_values(home_stats) and not has_technical_values(away_stats):
        return None

    home_stats = finalize_technical_stats(home_stats)
    away_stats = finalize_technical_stats(away_stats)
    return {
        "home": home_name,
        "away": away_name,
        "date": event.get("date") or competition.get("date"),
        "technical_source_url": source_url,
        "technical_stats": {
            "available": True,
            "source_name": SOURCE_NAME,
            "source_url": source_url,
            "home": home_stats,
            "away": away_stats,
            "referee": referee_name(summary),
        },
    }


def technical_stats_from_summary(summary: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    by_team: Dict[str, Dict[str, float]] = {}
    for team_row in ((summary or {}).get("boxscore") or {}).get("teams") or []:
        team = (team_row.get("team") or {}).get("displayName")
        if team:
            by_team[team] = normalize_technical_stats(team_row.get("statistics") or [])
    return by_team


def normalize_technical_stats(raw_stats: List[Dict[str, Any]]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    for item in raw_stats:
        key = TECHNICAL_STAT_MAP.get(str(item.get("name") or ""))
        if not key:
            continue
        value = parse_stat_number(item.get("value", item.get("displayValue")))
        if value is not None:
            normalized[key] = value
    return normalized


def parse_stat_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def substitution_counts(summary: Optional[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in (summary or {}).get("keyEvents") or []:
        event_type = ((item.get("type") or {}).get("type") or "").lower()
        if event_type != "substitution":
            continue
        team = (item.get("team") or {}).get("displayName")
        if team:
            counts[team] = counts.get(team, 0) + 1
    if counts:
        return counts
    for roster in (summary or {}).get("rosters") or []:
        team = (roster.get("team") or {}).get("displayName")
        if not team:
            continue
        counts[team] = sum(1 for player in roster.get("roster") or [] if player.get("subbedIn"))
    return counts


def referee_name(summary: Optional[Dict[str, Any]]) -> Optional[str]:
    officials = ((summary or {}).get("gameInfo") or {}).get("officials") or []
    for official in officials:
        position = (official.get("position") or {}).get("name") or ""
        if position.lower() == "referee":
            return official.get("displayName") or official.get("fullName")
    return None


def has_technical_values(stats: Dict[str, float]) -> bool:
    return any(key in stats for key in ("possession_pct", "shots", "shots_on_target", "corners", "tackles", "yellow_cards", "red_cards", "substitutions"))


def finalize_technical_stats(stats: Dict[str, float]) -> Dict[str, float]:
    finalized = dict(stats)
    shots = float(finalized.get("shots") or 0.0)
    shots_on_target = float(finalized.get("shots_on_target") or 0.0)
    corners = float(finalized.get("corners") or 0.0)
    finalized["xg_proxy"] = round(max(0.05, shots * 0.07 + shots_on_target * 0.16 + corners * 0.025), 2)
    return finalized


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
        if "home_score" not in event or "away_score" not in event:
            continue
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


def build_technical_results(matches: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    technical_results: Dict[str, Dict[str, Any]] = {}
    known_teams = sorted(
        {
            team
            for match in matches
            for team in (match.get("team1"), match.get("team2"))
            if team
        }
    )
    for event in events:
        technical = event.get("technical_stats") or {}
        if not technical.get("available"):
            continue
        match = match_for_event(matches, event, known_teams)
        if not match:
            continue
        team1 = canonicalize_team(match.get("team1", ""), known_teams)
        home = canonicalize_team(event.get("home", ""), known_teams)
        home_stats = technical.get("home") or {}
        away_stats = technical.get("away") or {}
        if team1 == home:
            team1_stats, team2_stats = home_stats, away_stats
        else:
            team1_stats, team2_stats = away_stats, home_stats
        technical_results[str(match["id"])] = {
            "available": True,
            "source_name": technical.get("source_name") or SOURCE_NAME,
            "source_url": event.get("technical_source_url") or technical.get("source_url") or ESPN_SCOREBOARD_URL,
            "team1": team1_stats,
            "team2": team2_stats,
            "referee": technical.get("referee"),
            "synced_at": now_iso(),
        }
    return technical_results


def match_event(
    matches: List[Dict[str, Any]], event: Dict[str, Any], known_teams: List[str]
) -> Optional[Tuple[Dict[str, Any], int, int]]:
    match = match_for_event(matches, event, known_teams)
    if not match:
        return None
    team1 = canonicalize_team(match.get("team1", ""), known_teams)
    home = canonicalize_team(event.get("home", ""), known_teams)
    if team1 == home:
        return match, int(event["home_score"]), int(event["away_score"])
    return match, int(event["away_score"]), int(event["home_score"])


def match_for_event(matches: List[Dict[str, Any]], event: Dict[str, Any], known_teams: List[str]) -> Optional[Dict[str, Any]]:
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

    return min(candidates, key=lambda item: item[0])[1]


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
