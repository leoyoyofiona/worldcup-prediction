from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .cache import now_iso
from .config import MODEL_VERSION
from .model import (
    OFFICIAL_KNOCKOUT_SLOTS,
    apply_actual_results,
    apply_post_match_calibration,
    apply_projected_knockout_matches,
    apply_technical_calibration,
    actual_knockout_result,
    build_technical_profiles,
    build_prediction_performance,
    build_post_match_calibration,
    build_tournament_projection,
    canonicalize_team,
    is_placeholder_team,
    match_status,
)


ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"
SOURCE_ID = "espn_live_results"
SOURCE_NAME = "ESPN 世界杯实时比分/技术统计"
FALLBACK_SOURCE_NAME = "公开淘汰赛赛果兜底"
FALLBACK_SOURCE_URL = "https://www.espn.com/soccer/bracket"
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


def sync_live_results(cache: Dict[str, Any], include_technical: bool = True) -> Dict[str, Any]:
    payload = deepcopy(cache)
    matches = payload.get("matches") or []
    fallback_events = static_knockout_events()

    for match in matches:
        match["status"] = match_status(match.get("starts_at"))

    apply_live_results_iteratively(payload, matches, fallback_events)
    events, status = fetch_espn_completed_events(
        include_technical=include_technical,
        target_dates=live_event_dates(matches),
    )
    events = fallback_events + events

    actual_results = apply_live_results_iteratively(payload, matches, events)
    technical_results = build_technical_results(matches, events)
    for match in matches:
        technical = technical_results.get(str(match.get("id")))
        if technical:
            match["technical_stats"] = technical

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
    if include_technical or technical_results:
        summary["technical_stat_match_count"] = len(technical_results)
        summary["technical_stat_team_count"] = len(technical_profiles)
    summary["live_result_synced_at"] = payload["generated_at"]
    summary["tournament_synced_at"] = payload["generated_at"]

    status["message"] = (
        f"已同步 {len(actual_results)} 场已完赛比分，{len(technical_results)} 场技术统计"
        if include_technical
        else f"已快速同步 {len(actual_results)} 场已完赛比分"
    )
    payload["sources"] = upsert_source(payload.get("sources") or [], status)
    return payload


def apply_live_results_iteratively(
    payload: Dict[str, Any],
    matches: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    max_passes: int = 6,
) -> Dict[str, Dict[str, Any]]:
    actual_results: Dict[str, Dict[str, Any]] = {}
    for _ in range(max_passes):
        before = live_sync_snapshot(matches)
        actual_results = build_actual_results(matches, events)
        apply_actual_results(matches, actual_results)
        resolve_actual_knockout_slots(matches)
        if live_sync_snapshot(matches) == before:
            break
    actual_results = build_actual_results(matches, events)
    apply_actual_results(matches, actual_results)
    rebuild_tournament(payload, matches)
    return actual_results


def live_sync_snapshot(matches: List[Dict[str, Any]]) -> Tuple[Tuple[Any, ...], ...]:
    return tuple(
        (
            match.get("id"),
            match.get("team1"),
            match.get("team2"),
            (match.get("actual_score") or {}).get("score"),
            (match.get("actual_score") or {}).get("regular_time_score"),
            (match.get("actual_score") or {}).get("extra_time_score"),
            (match.get("actual_score") or {}).get("penalty_score"),
        )
        for match in matches
    )


def static_knockout_events() -> List[Dict[str, Any]]:
    rows = [
        ("2026-06-28T20:00Z", "South Africa", "Canada", 0, 1, 0, 1, 0, 0, None),
        ("2026-06-29T17:00Z", "Brazil", "Japan", 2, 1, 2, 1, 0, 0, None),
        ("2026-06-29T20:00Z", "Germany", "Paraguay", 1, 1, 1, 1, 0, 0, "6-8"),
        ("2026-06-29T23:00Z", "Netherlands", "Morocco", 1, 1, 1, 1, 0, 0, "4-6"),
        ("2026-06-30T17:00Z", "Ivory Coast", "Norway", 1, 2, 1, 2, 0, 0, None),
        ("2026-06-30T20:00Z", "France", "Sweden", 3, 0, 3, 0, 0, 0, None),
        ("2026-06-30T23:00Z", "Mexico", "Ecuador", 2, 0, 2, 0, 0, 0, None),
        ("2026-07-01T17:00Z", "England", "Congo DR", 2, 1, 2, 1, 0, 0, None),
        ("2026-07-01T20:00Z", "Belgium", "Senegal", 3, 2, 2, 2, 1, 0, None),
        ("2026-07-01T23:00Z", "United States", "Bosnia-Herzegovina", 2, 0, 2, 0, 0, 0, None),
        ("2026-07-02T17:00Z", "Spain", "Austria", 3, 0, 3, 0, 0, 0, None),
        ("2026-07-02T20:00Z", "Portugal", "Croatia", 2, 1, 2, 1, 0, 0, None),
        ("2026-07-02T23:00Z", "Switzerland", "Algeria", 2, 0, 2, 0, 0, 0, None),
        ("2026-07-03T17:00Z", "Australia", "Egypt", 1, 1, 1, 1, 0, 0, "4-8"),
        ("2026-07-03T20:00Z", "Argentina", "Cape Verde", 3, 2, 1, 1, 2, 1, None),
        ("2026-07-03T23:00Z", "Colombia", "Ghana", 1, 0, 1, 0, 0, 0, None),
        ("2026-07-04T17:00Z", "Canada", "Morocco", 0, 3, 0, 3, 0, 0, None),
        ("2026-07-04T21:00Z", "Paraguay", "France", 0, 1, 0, 1, 0, 0, None),
        ("2026-07-05T20:00Z", "Brazil", "Norway", 1, 2, 1, 2, 0, 0, None),
        ("2026-07-06T01:00Z", "Mexico", "England", 2, 3, 2, 3, 0, 0, None),
        ("2026-07-06T19:00Z", "Portugal", "Spain", 0, 1, 0, 1, 0, 0, None),
        ("2026-07-07T00:00Z", "United States", "Belgium", 1, 4, 1, 4, 0, 0, None),
        ("2026-07-07T16:00Z", "Argentina", "Egypt", 3, 2, 3, 2, 0, 0, None),
        ("2026-07-07T20:00Z", "Switzerland", "Colombia", 0, 0, 0, 0, 0, 0, "8-6"),
        ("2026-07-09T20:00Z", "France", "Morocco", 2, 0, 2, 0, 0, 0, None),
        ("2026-07-10T19:00Z", "Spain", "Belgium", 2, 1, 2, 1, 0, 0, None),
        ("2026-07-11T21:00Z", "Norway", "England", 1, 2, 1, 1, 0, 1, None),
        ("2026-07-12T01:00Z", "Argentina", "Switzerland", 3, 1, 1, 1, 2, 0, None),
        ("2026-07-14T19:00Z", "France", "Spain", 0, 2, 0, 2, 0, 0, None),
        ("2026-07-15T19:00Z", "England", "Argentina", 1, 2, 1, 2, 0, 0, None),
        ("2026-07-18T21:00Z", "France", "England", 4, 6, 4, 6, 0, 0, None),
        ("2026-07-19T19:00Z", "Spain", "Argentina", 1, 0, 0, 0, 1, 0, None),
    ]
    return [
        static_event(date_text, home, away, home_score, away_score, home_regular, away_regular, home_extra, away_extra, penalty)
        for date_text, home, away, home_score, away_score, home_regular, away_regular, home_extra, away_extra, penalty in rows
    ]


def static_event(
    date_text: str,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    home_regular: int,
    away_regular: int,
    home_extra: int,
    away_extra: int,
    penalty_score: Optional[str],
) -> Dict[str, Any]:
    home_penalty, away_penalty = parse_penalty_score(penalty_score)
    return {
        "home": home,
        "away": away,
        "home_score": home_score,
        "away_score": away_score,
        "home_regular_score": home_regular,
        "away_regular_score": away_regular,
        "regular_time_score": f"{home_regular}-{away_regular}",
        "home_extra_score": home_extra,
        "away_extra_score": away_extra,
        "extra_time_score": f"{home_extra}-{away_extra}" if home_extra or away_extra else None,
        "home_penalty_score": home_penalty,
        "away_penalty_score": away_penalty,
        "penalty_score": penalty_score,
        "date": date_text,
        "source_name": FALLBACK_SOURCE_NAME,
        "source_url": FALLBACK_SOURCE_URL,
    }


def parse_penalty_score(score: Optional[str]) -> Tuple[int, int]:
    if not score:
        return 0, 0
    parts = score.split("-", 1)
    if len(parts) != 2:
        return 0, 0
    return safe_score(parts[0]) or 0, safe_score(parts[1]) or 0


def resolve_actual_knockout_slots(matches: List[Dict[str, Any]]) -> bool:
    winners: Dict[int, str] = {}
    losers: Dict[int, str] = {}
    changed = False
    for match in sorted((item for item in matches if item.get("is_knockout")), key=lambda item: int(item.get("index") or 0)):
        index = int(match.get("index") or 0)
        official_slot1, official_slot2 = OFFICIAL_KNOCKOUT_SLOTS.get(index, (None, None))
        slot1 = str(match.get("slot_team1") or official_slot1 or match.get("team1") or "")
        slot2 = str(match.get("slot_team2") or official_slot2 or match.get("team2") or "")
        team1 = resolve_actual_slot(slot1, winners, losers) or concrete_team(match.get("team1"))
        team2 = resolve_actual_slot(slot2, winners, losers) or concrete_team(match.get("team2"))
        if team1 and team2:
            if match.get("team1") != team1 or match.get("team2") != team2 or not match.get("teams_confirmed"):
                match["team1"] = team1
                match["team2"] = team2
                match["teams_confirmed"] = True
                changed = True
        if not team1 or not team2:
            continue
        actual_result = actual_knockout_result(match, team1, team2)
        if actual_result:
            winners[index], losers[index] = actual_result
    return changed


def resolve_actual_slot(slot: str, winners: Dict[int, str], losers: Dict[int, str]) -> Optional[str]:
    match = re.fullmatch(r"W(\d{2,3})", (slot or "").strip().upper())
    if match:
        return winners.get(int(match.group(1)))
    match = re.fullmatch(r"L(\d{2,3})", (slot or "").strip().upper())
    if match:
        return losers.get(int(match.group(1)))
    return concrete_team(slot)


def concrete_team(team: Any) -> Optional[str]:
    value = str(team or "").strip()
    if not value or is_placeholder_team(value):
        return None
    return canonicalize_team(value)


def rebuild_tournament(payload: Dict[str, Any], matches: List[Dict[str, Any]]) -> None:
    teams = payload.get("filters", {}).get("teams") or sorted(payload.get("teams", {}).keys())
    team_stats = payload.get("teams") or {}
    if not teams or not team_stats:
        return
    market_scores = collect_signal_scores(matches, "market")
    betting_scores = collect_signal_scores(matches, "betting_market")
    context_scores = collect_signal_scores(matches, "match_context")
    rankings = collect_rankings(matches)
    tournament = build_tournament_projection(
        matches,
        teams,
        team_stats,
        market_scores,
        betting_scores,
        rankings,
        context_scores,
    )
    apply_projected_knockout_matches(matches, tournament)
    payload["tournament"] = tournament


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


def live_event_start_date(matches: List[Dict[str, Any]]) -> date:
    dates = live_event_dates(matches)
    return min(dates) if dates else TOURNAMENT_START


def live_event_dates(matches: List[Dict[str, Any]]) -> List[date]:
    knockout_dates: List[date] = []
    other_dates: List[date] = []
    for match in matches:
        starts_at = parse_datetime(match.get("starts_at"))
        if not starts_at:
            continue
        if match_status(match.get("starts_at")) != "已结束":
            continue
        if match.get("actual_score"):
            continue
        dates = [starts_at.date() - timedelta(days=1), starts_at.date()]
        if match.get("is_knockout"):
            knockout_dates.extend(dates)
        else:
            other_dates.extend(dates)
    today = datetime.now(timezone.utc).date()
    recent_dates = [today - timedelta(days=1), today, today + timedelta(days=1)]
    selected_dates = knockout_dates or other_dates
    selected_dates.extend(recent_dates)
    return sorted({day for day in selected_dates if TOURNAMENT_START <= day <= today + timedelta(days=1)}, reverse=True)


def fetch_espn_completed_events(
    include_technical: bool = True,
    start_date: Optional[date] = None,
    target_dates: Optional[List[date]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    fetched_bytes = 0
    last_url = ESPN_SCOREBOARD_URL
    failures: List[str] = []
    today = datetime.now(timezone.utc).date() + timedelta(days=1)
    if target_dates:
        fetch_dates = sorted({day for day in target_dates if TOURNAMENT_START <= day <= today}, reverse=True)[:80]
    else:
        first_day = max(TOURNAMENT_START, start_date or TOURNAMENT_START)
        if first_day > today:
            first_day = today
        days = max(0, min((today - first_day).days, 80))
        fetch_dates = [first_day + timedelta(days=offset) for offset in range(days + 1)]

    timeout = httpx.Timeout(5.0, connect=3.0)
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "worldcup-predictor/1.0"}) as client:
        for current in fetch_dates:
            params = {"dates": current.strftime("%Y%m%d")}
            try:
                response = client.get(ESPN_SCOREBOARD_URL, params=params)
                last_url = str(response.url)
                response.raise_for_status()
                fetched_bytes += len(response.content)
                data = response.json()
            except Exception as exc:
                failures.append(f"{current.isoformat()} {type(exc).__name__}")
                continue
            for raw_event in data.get("events") or []:
                summary = fetch_espn_summary(client, raw_event) if include_technical else None
                technical = parse_espn_technical_event(raw_event, last_url, summary) if include_technical else None
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
        "ok": bool(events),
        "using_cache": False,
        "fetched_at": now_iso(),
        "bytes": fetched_bytes,
        "message": "；".join(failures[:3]) if failures else "",
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

    breakdown = score_breakdown_from_event(competition, home, away, home_score, away_score)
    return {
        "home": team_name(home),
        "away": team_name(away),
        "home_score": home_score,
        "away_score": away_score,
        **breakdown,
        "date": event.get("date") or competition.get("date"),
        "source_url": source_url,
    }


def score_breakdown_from_event(
    competition: Dict[str, Any],
    home: Dict[str, Any],
    away: Dict[str, Any],
    home_score: int,
    away_score: int,
) -> Dict[str, Any]:
    home_id = str((home.get("team") or {}).get("id") or home.get("id") or "")
    away_id = str((away.get("team") or {}).get("id") or away.get("id") or "")
    regular = {"home": 0, "away": 0}
    extra = {"home": 0, "away": 0}
    shootout = {
        "home": safe_score(home.get("shootoutScore") or home.get("shootout_score")) or 0,
        "away": safe_score(away.get("shootoutScore") or away.get("shootout_score")) or 0,
    }
    saw_goal_details = False

    for detail in competition.get("details") or []:
        if not detail.get("scoringPlay"):
            continue
        value = safe_score(detail.get("scoreValue"))
        if not value:
            continue
        team_id = str((detail.get("team") or {}).get("id") or "")
        side = "home" if team_id == home_id else "away" if team_id == away_id else None
        if not side:
            continue
        saw_goal_details = True
        if detail.get("shootout"):
            shootout[side] += value
            continue
        clock_value = float((detail.get("clock") or {}).get("value") or 0.0)
        if clock_value and clock_value > 90 * 60:
            extra[side] += value
        else:
            regular[side] += value

    status = (competition.get("status") or {}).get("type") or {}
    is_after_extra = "AET" in {str(status.get("detail") or ""), str(status.get("shortDetail") or "")} or "EXTRA" in str(status.get("name") or "").upper()
    if not saw_goal_details:
        regular = {"home": home_score, "away": away_score}
        extra = {"home": 0, "away": 0}
    return {
        "home_regular_score": regular["home"],
        "away_regular_score": regular["away"],
        "regular_time_score": f"{regular['home']}-{regular['away']}",
        "home_extra_score": extra["home"],
        "away_extra_score": extra["away"],
        "extra_time_score": f"{extra['home']}-{extra['away']}" if is_after_extra or extra["home"] or extra["away"] else None,
        "home_penalty_score": shootout["home"],
        "away_penalty_score": shootout["away"],
        "penalty_score": f"{shootout['home']}-{shootout['away']}" if shootout["home"] or shootout["away"] else None,
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
        team1_is_home = canonicalize_team(match.get("team1", ""), known_teams) == canonicalize_team(event.get("home", ""), known_teams)
        regular_team1, regular_team2 = score_pair_for_schedule(event, "regular", team1_is_home, team1_goals, team2_goals)
        extra_team1, extra_team2 = score_pair_for_schedule(event, "extra", team1_is_home, 0, 0)
        penalty_team1, penalty_team2 = score_pair_for_schedule(event, "penalty", team1_is_home, 0, 0)
        actual_results[str(match["id"])] = {
            "team1_name": match.get("team1"),
            "team2_name": match.get("team2"),
            "team1": team1_goals,
            "team2": team2_goals,
            "score": f"{team1_goals}-{team2_goals}",
            "regular_time_team1": regular_team1,
            "regular_time_team2": regular_team2,
            "regular_time_score": f"{regular_team1}-{regular_team2}",
            "extra_time_team1": extra_team1,
            "extra_time_team2": extra_team2,
            "extra_time_score": f"{extra_team1}-{extra_team2}" if event.get("extra_time_score") else None,
            "penalty_team1": penalty_team1,
            "penalty_team2": penalty_team2,
            "penalty_score": f"{penalty_team1}-{penalty_team2}" if event.get("penalty_score") else None,
            "source_name": event.get("source_name") or SOURCE_NAME,
            "source_url": event.get("source_url") or ESPN_SCOREBOARD_URL,
            "verified_at": now_iso(),
        }
    return actual_results


def score_pair_for_schedule(
    event: Dict[str, Any],
    prefix: str,
    team1_is_home: bool,
    fallback_team1: int,
    fallback_team2: int,
) -> Tuple[int, int]:
    home_value = safe_score(event.get(f"home_{prefix}_score"))
    away_value = safe_score(event.get(f"away_{prefix}_score"))
    if home_value is None or away_value is None:
        return fallback_team1, fallback_team2
    return (home_value, away_value) if team1_is_home else (away_value, home_value)


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
