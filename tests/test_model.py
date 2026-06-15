from app.model import (
    build_betting_scores,
    build_market_scores,
    build_post_match_calibration,
    build_predictions,
    build_prediction_performance,
    build_team_stats,
    build_world_cup_profiles,
    context_attack_multiplier,
    context_defense_multiplier,
    apply_post_match_calibration,
    expected_group_tables,
    off_field_signal,
    rule_adaptation_adjustment,
    is_placeholder_team,
    parse_results_csv,
    parse_schedule,
    parse_world_cup_matches_csv,
    predict_match,
    score_matrix,
)


SCHEDULE = """
{
  "name": "World Cup 2026",
  "matches": [
    {
      "round": "Matchday 1",
      "date": "2026-06-11",
      "time": "13:00 UTC-6",
      "team1": "Brazil",
      "team2": "Canada",
      "group": "Group A",
      "ground": "Toronto"
    },
    {
      "round": "Round of 32",
      "date": "2026-06-28",
      "time": "18:00 UTC-4",
      "team1": "Winner Group A",
      "team2": "Runner-up Group B",
      "ground": "New York"
    }
  ]
}
"""


RESULTS = """date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
2024-01-01,Brazil,Canada,3,0,Friendly,Rio de Janeiro,Brazil,FALSE
2024-02-01,Brazil,Argentina,2,1,FIFA World Cup qualification,Sao Paulo,Brazil,FALSE
2024-03-01,Canada,Brazil,1,1,Friendly,Toronto,Canada,FALSE
2024-04-01,Canada,Argentina,0,2,Friendly,Toronto,Canada,FALSE
"""

WORLD_CUP_MATCHES = """Year,Datetime,Stage,Stadium,City,Home Team Name,Home Team Goals,Away Team Goals,Away Team Name,Attendance,Half-time Home Goals,Half-time Away Goals,Referee,Assistant 1,Assistant 2,RoundID,MatchID,Home Team Initials,Away Team Initials
2014,08 Jul 2014 - 17:00 ,Semi-finals,Mineirao,Belo Horizonte ,Brazil,1,7,Germany,58141,0,5,REF,A1,A2,255955,300186474,BRA,GER
2014,13 Jul 2014 - 16:00 ,Final,Maracana,Rio De Janeiro ,Germany,1,0,Argentina,74738,0,0,REF,A1,A2,255959,300186501,GER,ARG
"""


def test_score_matrix_probabilities_sum_to_one():
    _, probabilities = score_matrix(1.4, 0.9)
    assert round(sum(probabilities.values()), 6) == 1.0
    assert probabilities["team1_win"] > probabilities["team2_win"]


def test_build_market_scores_clips_adjustment():
    scores = build_market_scores(
        ["Brazil", "Canada"],
        ["义乌 世界杯 球衣 订单 巴西 巴西 Brazil flag jersey orders"],
    )
    assert scores["Brazil"]["adjustment"] <= 25.0
    assert scores["Brazil"]["adjustment"] > scores["Canada"]["adjustment"]


def test_build_betting_scores_uses_nearby_odds():
    scores = build_betting_scores(
        ["Brazil", "Canada"],
        ["World Cup winner odds Brazil 4.50 Argentina 6/1 Canada +8000 outright betting odds"],
    )
    assert scores["Brazil"]["available"] is True
    assert scores["Brazil"]["best_decimal_odds"] == 4.5
    assert scores["Brazil"]["adjustment"] > scores["Canada"]["adjustment"]


def test_knockout_placeholder_detection():
    assert is_placeholder_team("1A") is True
    assert is_placeholder_team("3A/B/C/D/F") is True
    assert is_placeholder_team("W101") is True
    assert is_placeholder_team("Brazil") is False


def test_prediction_contains_probabilities():
    schedule = parse_schedule(SCHEDULE)
    teams = ["Brazil", "Canada"]
    results = parse_results_csv(RESULTS, teams)
    stats = build_team_stats(results, teams)
    assert "goldman_adjustment" in stats["Brazil"]
    assert "goldman_attack" in stats["Brazil"]
    markets = build_market_scores(teams, ["义乌 世界杯 球衣 订单 加拿大"])
    prediction = predict_match(schedule[0], stats, markets, {})
    assert prediction["teams_confirmed"] is True
    assert prediction["probabilities"]["team1_win"] > 0
    assert prediction["predicted_score"] != "待定"
    assert prediction["contributors"]


def test_world_cup_local_csv_builds_stage_profile():
    rows = parse_world_cup_matches_csv(WORLD_CUP_MATCHES, ["Brazil", "Germany", "Argentina"])
    assert len(rows) == 2
    assert rows[0]["tournament"] == "FIFA World Cup"
    profiles = build_world_cup_profiles(rows, ["Brazil", "Germany", "Argentina"])
    assert profiles["Germany"]["world_cup_local_matches"] == 2
    assert profiles["Germany"]["world_cup_stage_adjustment"] > profiles["Brazil"]["world_cup_stage_adjustment"]


def test_placeholder_team_does_not_predict():
    schedule = parse_schedule(SCHEDULE)
    teams = ["Brazil", "Canada"]
    results = parse_results_csv(RESULTS, teams)
    stats = build_team_stats(results, teams)
    prediction = predict_match(schedule[1], stats, {}, {})
    assert prediction["teams_confirmed"] is False
    assert prediction["probabilities"] is None


def test_build_predictions_payload_shape():
    payload = build_predictions(
        {
            "schedule_openfootball": SCHEDULE,
            "results_history": RESULTS,
            "worldcup_matches_local": WORLD_CUP_MATCHES,
            "yiwu_index": "义乌 世界杯 球衣 订单 巴西",
        },
        [],
    )
    assert payload["summary"]["match_count"] == 2
    assert payload["filters"]["teams"] == ["Brazil", "Canada"]
    assert payload["matches"][0]["probabilities"]
    assert payload["tournament"]["simulations"] == 50000
    assert "matchup_rounds" in payload["tournament"]
    assert "betting_signal_available" in payload["summary"]
    assert payload["summary"]["world_cup_rows"] == 2


def test_prediction_performance_counts_hits():
    matches = [
        {
            "id": "m1",
            "team1": "Mexico",
            "team2": "South Africa",
            "predicted_score": "2-0",
            "actual_score": {"team1": 2, "team2": 0, "score": "2-0"},
            "prediction_result": {"outcome_hit": True, "exact_score_hit": True, "goal_error": 0},
        },
        {
            "id": "m2",
            "team1": "South Korea",
            "team2": "Czech Republic",
            "predicted_score": "2-1",
            "actual_score": {"team1": 2, "team2": 1, "score": "2-1"},
            "prediction_result": {"outcome_hit": True, "exact_score_hit": True, "goal_error": 0},
        },
    ]
    performance = build_prediction_performance(matches)
    assert performance["sample_size"] == 2
    assert performance["outcome_accuracy"] == 100.0
    assert performance["exact_score_accuracy"] == 100.0


def test_group_table_uses_actual_scores_before_expected_points():
    matches = [
        {
            "group": "Group A",
            "teams_confirmed": True,
            "team1": "Mexico",
            "team2": "South Africa",
            "probabilities": {"team1_win": 0.0, "draw": 0.0, "team2_win": 100.0},
            "expected_goals": {"team1": 0.1, "team2": 4.0},
            "actual_score": {"team1": 2, "team2": 0, "score": "2-0"},
        }
    ]
    rows = expected_group_tables(matches)["A"]
    assert rows[0]["team"] == "Mexico"
    assert rows[0]["points"] == 3.0
    assert rows[0]["gf"] == 2.0
    assert rows[1]["team"] == "South Africa"
    assert rows[1]["points"] == 0.0


def test_context_adjustments_are_bounded_and_explainable():
    iran = off_field_signal("Iran")
    assert iran["available"] is True
    assert -18.0 <= iran["adjustment"] <= 18.0
    assert iran["factors"][0]["source_url"]

    rule_score = rule_adaptation_adjustment(
        {
            "goldman_attack": 1.35,
            "goldman_defense": 0.8,
            "competitive_points_rate": 0.7,
        }
    )
    assert -10.0 <= rule_score <= 10.0
    assert rule_score > 0

    travel_risk = {"off_field": -18.0, "rules": 0.0}
    rule_edge = {"off_field": 0.0, "rules": 10.0}
    assert context_attack_multiplier(travel_risk) < 1.0
    assert context_defense_multiplier(travel_risk) > 1.0
    assert context_attack_multiplier(rule_edge) > 1.0


def test_post_match_calibration_updates_future_predictions_only():
    completed_template = {
        "teams_confirmed": True,
        "probabilities": {"team1_win": 62.0, "draw": 19.0, "team2_win": 19.0},
        "favorite": "Brazil",
        "expected_goals": {"team1": 1.6, "team2": 0.8},
        "predicted_score": "2-1",
        "contributors": [],
    }
    matches = [
        {
            **completed_template,
            "id": "done-1",
            "team1": "Germany",
            "team2": "Brazil",
            "actual_score": {"team1": 7, "team2": 1, "score": "7-1"},
        },
        {
            **completed_template,
            "id": "done-2",
            "team1": "Netherlands",
            "team2": "Japan",
            "actual_score": {"team1": 2, "team2": 2, "score": "2-2"},
        },
        {
            **completed_template,
            "id": "done-3",
            "team1": "United States",
            "team2": "Paraguay",
            "actual_score": {"team1": 4, "team2": 1, "score": "4-1"},
        },
        {
            **completed_template,
            "id": "done-4",
            "team1": "Sweden",
            "team2": "Nigeria",
            "actual_score": {"team1": 5, "team2": 0, "score": "5-0"},
        },
        {
            "id": "future-1",
            "teams_confirmed": True,
            "team1": "Brazil",
            "team2": "Canada",
            "probabilities": {"team1_win": 65.0, "draw": 18.0, "team2_win": 17.0},
            "favorite": "Brazil",
            "expected_goals": {"team1": 1.7, "team2": 0.7},
            "predicted_score": "2-0",
            "contributors": [],
            "effective_ratings": {"team1": 1700.0, "team2": 1540.0},
        },
    ]
    calibration = build_post_match_calibration(matches)
    original_done_score = matches[0]["predicted_score"]
    original_future_total = sum(matches[-1]["expected_goals"].values())

    apply_post_match_calibration(matches, calibration)

    assert calibration["available"] is True
    assert matches[0]["predicted_score"] == original_done_score
    assert sum(matches[-1]["expected_goals"].values()) != original_future_total
    assert matches[-1]["post_match_calibration"]["available"] is True
    assert any(item["name"] == "赛后复盘校准" for item in matches[-1]["contributors"])


def test_group_stage_pressure_changes_remaining_group_match():
    matches = [
        {
            "id": "g1",
            "group": "Group A",
            "teams_confirmed": True,
            "team1": "Mexico",
            "team2": "Canada",
            "actual_score": {"team1": 2, "team2": 0, "score": "2-0"},
        },
        {
            "id": "g2",
            "group": "Group A",
            "teams_confirmed": True,
            "team1": "Brazil",
            "team2": "South Africa",
            "actual_score": {"team1": 1, "team2": 1, "score": "1-1"},
        },
        {
            "id": "g3",
            "group": "Group A",
            "teams_confirmed": True,
            "team1": "Canada",
            "team2": "Brazil",
            "probabilities": {"team1_win": 22.0, "draw": 26.0, "team2_win": 52.0},
            "favorite": "Brazil",
            "expected_goals": {"team1": 0.9, "team2": 1.5},
            "predicted_score": "1-2",
            "contributors": [],
            "effective_ratings": {"team1": 1530.0, "team2": 1710.0},
        },
        {
            "id": "done-1",
            "group": "Group B",
            "teams_confirmed": True,
            "team1": "Germany",
            "team2": "Japan",
            "probabilities": {"team1_win": 62.0, "draw": 19.0, "team2_win": 19.0},
            "expected_goals": {"team1": 1.6, "team2": 0.8},
            "predicted_score": "2-1",
            "actual_score": {"team1": 7, "team2": 1, "score": "7-1"},
        },
        {
            "id": "done-2",
            "group": "Group C",
            "teams_confirmed": True,
            "team1": "Netherlands",
            "team2": "Sweden",
            "probabilities": {"team1_win": 62.0, "draw": 19.0, "team2_win": 19.0},
            "expected_goals": {"team1": 1.6, "team2": 0.8},
            "predicted_score": "2-1",
            "actual_score": {"team1": 2, "team2": 2, "score": "2-2"},
        },
    ]
    calibration = {
        "available": True,
        "sample_size": 4,
        "goal_multiplier": 1.05,
        "draw_multiplier": 1.0,
        "high_total_multiplier": 1.0,
        "host_attack_multiplier": 1.0,
        "favorite_compression": 1.0,
    }
    original_canada_goals = matches[2]["expected_goals"]["team1"]

    apply_post_match_calibration(matches, calibration)

    assert matches[2]["expected_goals"]["team1"] > original_canada_goals
    assert matches[2]["group_stage_context"]["available"] is True
    assert any(item["name"] == "小组出线形势" for item in matches[2]["contributors"])
