from app.live_results import build_actual_results, parse_espn_event
from app.services import attach_betting_recommendations, beijing_date_key


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
