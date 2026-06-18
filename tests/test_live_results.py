from app.live_results import build_actual_results, build_technical_results, parse_espn_event, parse_espn_technical_event
from datetime import datetime, timezone

from app.model import apply_technical_calibration, build_technical_profiles
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


def test_parse_espn_technical_event_includes_match_stats_and_substitutions():
    event = {
        "id": "760436",
        "date": "2026-06-18T02:00Z",
        "competitions": [
            {
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"displayName": "Uzbekistan"},
                        "statistics": [
                            {"name": "possessionPct", "displayValue": "41.5"},
                            {"name": "totalShots", "displayValue": "8"},
                            {"name": "shotsOnTarget", "displayValue": "3"},
                        ],
                    },
                    {
                        "homeAway": "away",
                        "team": {"displayName": "Colombia"},
                        "statistics": [
                            {"name": "possessionPct", "displayValue": "58.5"},
                            {"name": "totalShots", "displayValue": "13"},
                            {"name": "shotsOnTarget", "displayValue": "5"},
                        ],
                    },
                ]
            }
        ],
    }
    summary = {
        "boxscore": {
            "teams": [
                {
                    "team": {"displayName": "Uzbekistan"},
                    "statistics": [
                        {"name": "wonCorners", "displayValue": "2"},
                        {"name": "totalTackles", "displayValue": "18"},
                        {"name": "yellowCards", "displayValue": "3"},
                        {"name": "redCards", "displayValue": "0"},
                    ],
                },
                {
                    "team": {"displayName": "Colombia"},
                    "statistics": [
                        {"name": "wonCorners", "displayValue": "6"},
                        {"name": "totalTackles", "displayValue": "11"},
                        {"name": "yellowCards", "displayValue": "1"},
                        {"name": "redCards", "displayValue": "0"},
                    ],
                },
            ]
        },
        "keyEvents": [
            {"type": {"type": "substitution"}, "team": {"displayName": "Uzbekistan"}},
            {"type": {"type": "substitution"}, "team": {"displayName": "Colombia"}},
            {"type": {"type": "substitution"}, "team": {"displayName": "Colombia"}},
        ],
    }
    parsed = parse_espn_technical_event(event, "https://example.test", summary)
    assert parsed["technical_stats"]["home"]["corners"] == 2.0
    assert parsed["technical_stats"]["away"]["substitutions"] == 2
    assert parsed["technical_stats"]["home"]["xg_proxy"] > 0


def test_technical_results_map_to_schedule_order_and_calibrate_future_match():
    matches = [
        {
            "id": "done",
            "team1": "Uzbekistan",
            "team2": "Colombia",
            "starts_at": "2026-06-18T02:00:00+00:00",
            "actual_score": {"team1": 1, "team2": 2, "score": "1-2"},
        },
        {
            "id": "future",
            "team1": "Colombia",
            "team2": "South Africa",
            "starts_at": "2026-06-22T02:00:00+00:00",
            "teams_confirmed": True,
            "expected_goals": {"team1": 1.5, "team2": 1.0},
            "probabilities": {"team1_win": 50.0, "draw": 25.0, "team2_win": 25.0},
            "technical_indicators": {"available": True, "team1": {"xg": 1.5, "shots": 11.0}, "team2": {"xg": 1.0, "shots": 8.0}},
        },
    ]
    events = [
        {
            "home": "Uzbekistan",
            "away": "Colombia",
            "date": "2026-06-18T02:00Z",
            "technical_source_url": "https://example.test",
            "technical_stats": {
                "available": True,
                "home": {"shots": 7.0, "shots_on_target": 2.0, "corners": 2.0, "tackles": 18.0, "yellow_cards": 3.0, "red_cards": 0.0, "substitutions": 5.0, "xg_proxy": 0.9},
                "away": {"shots": 16.0, "shots_on_target": 7.0, "corners": 6.0, "tackles": 11.0, "yellow_cards": 1.0, "red_cards": 0.0, "substitutions": 5.0, "xg_proxy": 2.2},
            },
        }
    ]
    technical = build_technical_results(matches, events)
    matches[0]["technical_stats"] = technical["done"]
    profiles = build_technical_profiles(matches)
    original_xg = matches[1]["expected_goals"]["team1"]
    apply_technical_calibration(matches, profiles)
    assert technical["done"]["team1"]["shots"] == 7.0
    assert profiles["Colombia"]["technical_adjustment"] > profiles["Uzbekistan"]["technical_adjustment"]
    assert matches[1]["expected_goals"]["team1"] > original_xg
    assert any(item["name"] == "技术统计修正" for item in matches[1]["contributors"])


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


def test_betting_days_include_xg_and_mixed_pass_plan():
    base_analysis = {
        "favorite": "team1_win",
        "model_probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
        "fair_odds": {"team1_win": 1.82, "draw": 4.0, "team2_win": 5.0},
        "value_threshold_odds": {"team1_win": 1.91, "draw": 4.2, "team2_win": 5.25},
    }
    matches = [
        {
            "id": f"match-{index}",
            "starts_at": f"2026-06-16T{10 + index:02d}:00:00+00:00",
            "teams_confirmed": True,
            "team1": f"Team {index}A",
            "team2": f"Team {index}B",
            "predicted_score": "2-1",
            "expected_goals": {"team1": 1.8, "team2": 1.1},
            "score_summary": {"expected_total_goals": 2.9, "over_2_5": 54.0, "both_teams_score": 51.0},
            "probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
            "betting_analysis": base_analysis,
        }
        for index in range(4)
    ]
    days = build_betting_days(matches, 50.0, now=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc))
    day = days[0]
    plan = day["mixed_pass_plan"]
    assert day["budget"] == 50.0
    assert day["target_profit"] == 10000.0
    assert day["matches"][0]["expected_goals"] == {"team1": 1.8, "team2": 1.1}
    assert day["matches"][0]["score_summary"]["expected_total_goals"] == 2.9
    assert plan["available"] is True
    assert plan["total_stake"] == 50.0
    assert [ticket["pass_type"] for ticket in plan["tickets"]] == ["4串1", "3串1", "3串1", "3串1", "3串1"]
    assert plan["target_gap"] > 0
    assert "达不到万元目标" in plan["feasibility"]
