from app.live_results import (
    apply_live_results_iteratively,
    build_actual_results,
    build_technical_results,
    parse_espn_event,
    parse_espn_technical_event,
)
from datetime import datetime, timezone

from app.model import apply_technical_calibration, build_technical_profiles
from app.services import beijing_date_key, build_betting_days, build_daily_match_recommendation


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
        "home_regular_score": 1,
        "away_regular_score": 1,
        "regular_time_score": "1-1",
        "home_extra_score": 0,
        "away_extra_score": 0,
        "extra_time_score": None,
        "home_penalty_score": 0,
        "away_penalty_score": 0,
        "penalty_score": None,
        "date": "2026-06-12T19:00Z",
        "source_url": "https://example.test",
    }


def test_parse_aet_espn_event_splits_regular_and_extra_time():
    event = {
        "date": "2026-07-03T22:00Z",
        "competitions": [
            {
                "status": {"type": {"completed": True, "detail": "AET", "shortDetail": "AET", "name": "STATUS_FINAL_AET"}},
                "competitors": [
                    {"homeAway": "home", "score": "3", "team": {"id": "202", "displayName": "Argentina"}},
                    {"homeAway": "away", "score": "2", "team": {"id": "2597", "displayName": "Cape Verde"}},
                ],
                "details": [
                    {"scoringPlay": True, "scoreValue": 1, "team": {"id": "202"}, "clock": {"value": 1682.0}},
                    {"scoringPlay": True, "scoreValue": 1, "team": {"id": "2597"}, "clock": {"value": 3518.0}},
                    {"scoringPlay": True, "scoreValue": 1, "team": {"id": "202"}, "clock": {"value": 5517.0}},
                    {"scoringPlay": True, "scoreValue": 1, "team": {"id": "2597"}, "clock": {"value": 6161.0}},
                    {"scoringPlay": True, "scoreValue": 1, "team": {"id": "202"}, "clock": {"value": 6631.0}},
                ],
            }
        ],
    }
    parsed = parse_espn_event(event, "https://example.test/aet")
    assert parsed["home_score"] == 3
    assert parsed["away_score"] == 2
    assert parsed["regular_time_score"] == "1-1"
    assert parsed["extra_time_score"] == "2-1"
    assert parsed["penalty_score"] is None


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


def test_build_actual_results_matches_turkiye_alias():
    matches = [
        {
            "id": "wc2026-022",
            "team1": "Turkey",
            "team2": "Paraguay",
            "starts_at": "2026-06-20T03:00:00+00:00",
        }
    ]
    events = [
        {
            "home": "Türkiye",
            "away": "Paraguay",
            "home_score": 0,
            "away_score": 1,
            "date": "2026-06-20T03:00Z",
            "source_url": "https://example.test/turkiye",
        }
    ]
    actuals = build_actual_results(matches, events)
    assert actuals["wc2026-022"]["score"] == "0-1"
    assert actuals["wc2026-022"]["team1_name"] == "Turkey"


def test_live_result_sync_resolves_knockout_placeholders_before_matching_later_round(monkeypatch):
    matches = [
        {
            "id": "m89",
            "index": 89,
            "round": "Round of 16",
            "is_knockout": True,
            "team1": "Paraguay",
            "team2": "France",
            "actual_score": {"team1": 0, "team2": 1, "score": "0-1"},
        },
        {
            "id": "m90",
            "index": 90,
            "round": "Round of 16",
            "is_knockout": True,
            "team1": "Canada",
            "team2": "Morocco",
            "actual_score": {"team1": 0, "team2": 3, "score": "0-3"},
        },
        {
            "id": "m97",
            "index": 97,
            "round": "Quarter-final",
            "is_knockout": True,
            "team1": "W89",
            "team2": "W90",
            "slot_team1": "W89",
            "slot_team2": "W90",
            "starts_at": "2026-07-09T20:00:00+00:00",
        },
    ]
    events = [
        {
            "home": "France",
            "away": "Morocco",
            "home_score": 2,
            "away_score": 0,
            "date": "2026-07-09T20:00Z",
            "source_url": "https://example.test/qf",
        }
    ]

    def fake_rebuild_tournament(payload, current_matches):
        for match in current_matches:
            if match.get("index") == 97:
                match["team1"] = "France"
                match["team2"] = "Morocco"
                match["teams_confirmed"] = True

    monkeypatch.setattr("app.live_results.rebuild_tournament", fake_rebuild_tournament)

    actuals = apply_live_results_iteratively({}, matches, events)

    assert actuals["m97"]["score"] == "2-0"
    assert matches[2]["actual_score"]["score"] == "2-0"


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


def test_beijing_day_and_daily_recommendation_payload():
    match = {
        "starts_at": "2026-06-14T23:00:00+00:00",
        "team1": "Ivory Coast",
        "team2": "Ecuador",
        "predicted_score": "2-1",
        "expected_goals": {"team1": 1.8, "team2": 1.1},
        "score_summary": {"expected_total_goals": 2.9, "over_2_5": 54.0, "over_3_5": 32.0, "both_teams_score": 51.0},
        "probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
        "betting_analysis": {
            "favorite": "team1_win",
            "model_probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
            "fair_odds": {"team1_win": 1.82, "draw": 4.0, "team2_win": 5.0},
            "value_threshold_odds": {"team1_win": 1.91, "draw": 4.2, "team2_win": 5.25},
        },
    }
    assert beijing_date_key(match) == "2026-06-15"
    recommendation = build_daily_match_recommendation(match)
    assert recommendation["total_goals"]["play_type"] == "总进球数"
    assert recommendation["score"]["selection"] == "2-1"
    assert recommendation["half_full"]["play_type"] == "半全场"
    assert recommendation["upset"]["play_type"] == "爆冷观察"
    assert "stake" not in recommendation["upset"]
    assert "possible_payout" not in recommendation["upset"]


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
    days = build_betting_days(matches, now=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc))
    assert days[0]["date"] == "2026-06-16"
    assert [match["id"] for match in days[0]["matches"]] == ["live", "today-1", "today-2"]
    assert days[0]["matches"][0]["bettable"] is False
    assert days[0]["recommendation_types"] == ["总进球数", "比分", "半全场", "爆冷观察"]
    assert all("daily_recommendation" in match for match in days[0]["matches"])
    assert all("betting_recommendation" not in match for match in days[0]["matches"])
    assert "budget" not in days[0]


def test_betting_days_include_xg_and_daily_analysis_picks():
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
            "score_summary": {"expected_total_goals": 2.9, "over_2_5": 54.0, "over_3_5": 32.0, "both_teams_score": 51.0},
            "probabilities": {"team1_win": 55.0, "draw": 25.0, "team2_win": 20.0},
            "betting_analysis": base_analysis,
        }
        for index in range(4)
    ]
    days = build_betting_days(matches, now=datetime(2026, 6, 16, 8, 0, tzinfo=timezone.utc))
    day = days[0]
    assert day["matches"][0]["expected_goals"] == {"team1": 1.8, "team2": 1.1}
    assert day["matches"][0]["score_summary"]["expected_total_goals"] == 2.9
    recommendation = day["matches"][0]["daily_recommendation"]
    assert recommendation["total_goals"]["selection"] in {"2-3球", "3球左右"}
    assert recommendation["score"]["selection"] == "2-1"
    assert recommendation["half_full"]["selection"] in {"平胜", "胜胜"}
    assert recommendation["upset"]["value_threshold_odds"] == 4.2
    assert "mixed_pass_plan" not in day
