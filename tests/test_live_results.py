from app.live_results import build_actual_results, parse_espn_event
from datetime import datetime, timezone

from app.services import attach_betting_recommendations, beijing_date_key, build_betting_days


def test_parse_completed_espn_event():
    event = {
        "date": "2026-06-12T19:00Z",
        "competitions": [
            {
                "status": {"type": {"completed": True}},
                "competitors": [
                    {"homeAway": "home", "score": "1", "team": {"displayName": "Canada"}},
                    {"homeAway": "away", "score": "1", "team": {"displayName": "Bosnia-Herzegovina"}},
                ],
            }
        ],
    }
    parsed = parse_espn_event(event, "https://example.test")
    assert parsed == {
        "home": "Canada",
        "away": "Bosnia-Herzegovina",
        "home_score": 1,
        "away_score": 1,
        "date": "2026-06-12T19:00Z",
        "source_url": "https://example.test",
    }


def test_build_actual_results_matches_aliases_and_preserves_schedule_order():
    matches = [
        {
            "id": "wc2026-002",
            "team1": "South Korea",
            "team2": "Czech Republic",
            "starts_at": "2026-06-12T02:00:00+00:00",
        },
        {
            "id": "wc2026-007",
            "team1": "Canada",
            "team2": "Bosnia & Herzegovina",
            "starts_at": "2026-06-12T19:00:00+00:00",
        },
    ]
    events = [
        {
            "home": "South Korea",
            "away": "Czechia",
            "home_score": 2,
            "away_score": 1,
            "date": "2026-06-12T02:00Z",
            "source_url": "https://example.test/1",
        },
        {
            "home": "Canada",
            "away": "Bosnia-Herzegovina",
            "home_score": 1,
            "away_score": 1,
            "date": "2026-06-12T19:00Z",
            "source_url": "https://example.test/2",
        },
    ]
    actuals = build_actual_results(matches, events)
    assert actuals["wc2026-002"]["score"] == "2-1"
    assert actuals["wc2026-007"]["score"] == "1-1"
    assert actuals["wc2026-007"]["team2_name"] == "Bosnia & Herzegovina"


def test_beijing_day_and_betting_recommendation_payload():
    match = {
        "starts_at": "2026-06-14T23:00:00+00:00",
        "team1": "Ivory Coast",
        "team2": "Ecuador",
        "probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
        "betting_analysis": {
            "favorite": "team1_win",
            "model_probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
            "fair_odds": {"team1_win": 1.82, "draw": 4.0, "team2_win": 5.0},
            "value_threshold_odds": {"team1_win": 1.91, "draw": 4.2, "team2_win": 5.25},
        },
    }
    assert beijing_date_key(match) == "2026-06-15"
    rows = attach_betting_recommendations([match], 100.0)
    recommendation = rows[0]["betting_recommendation"]
    assert recommendation["play_type"] == "竞彩足球胜平负"
    assert recommendation["stake"] == 100.0
    assert recommendation["reference_odds"] == 1.91
    assert recommendation["possible_payout"] == 191.0


def test_betting_days_use_today_beijing_and_exclude_started_matches():
    base_analysis = {
        "favorite": "team1_win",
        "model_probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
        "fair_odds": {"team1_win": 1.82, "draw": 4.0, "team2_win": 5.0},
        "value_threshold_odds": {"team1_win": 1.91, "draw": 4.2, "team2_win": 5.25},
    }
    matches = [
        {
            "id": "started",
            "starts_at": "2026-06-16T01:00:00+00:00",
            "teams_confirmed": True,
            "team1": "A",
            "team2": "B",
            "betting_analysis": base_analysis,
        },
        {
            "id": "today-1",
            "starts_at": "2026-06-16T12:00:00+00:00",
            "teams_confirmed": True,
            "team1": "C",
            "team2": "D",
            "betting_analysis": base_analysis,
        },
        {
            "id": "live",
            "starts_at": "2026-06-16T07:30:00+00:00",
            "teams_confirmed": True,
            "team1": "Live A",
            "team2": "Live B",
            "betting_analysis": base_analysis,
        },
        {
            "id": "today-2",
            "starts_at": "2026-06-16T15:00:00+00:00",
            "teams_confirmed": True,
            "team1": "E",
            "team2": "F",
            "betting_analysis": base_analysis,
        },
        {
            "id": "tomorrow",
            "starts_at": "2026-06-17T12:00:00+00:00",
            "teams_confirmed": True,
            "team1": "G",
            "team2": "H",
            "betting_analysis": base_analysis,
        },
    ]
    days = build_betting_days(matches, 100.0, now=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc))
    assert days[0]["date"] == "2026-06-16"
    assert [match["id"] for match in days[0]["matches"]] == ["live", "today-1", "today-2"]
    assert days[0]["matches"][0]["bettable"] is False
    assert days[0]["matches"][0]["betting_recommendation"]["stake"] == 0.0
    assert sum(match["betting_recommendation"]["stake"] for match in days[0]["matches"]) == 100.0
