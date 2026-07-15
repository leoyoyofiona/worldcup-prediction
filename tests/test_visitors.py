from app.visitors import ensure_minimum_total, record_visit, visitor_stats


def test_record_visit_counts_total_and_today(tmp_path):
    stats_file = tmp_path / "visitor_stats.json"

    first = record_visit(stats_file)
    second = record_visit(stats_file)
    current = visitor_stats(stats_file)

    assert first["tracked_visits"] == 1
    assert second["tracked_visits"] == 2
    assert current["total_visits"] == current["baseline_count"] + 2
    assert current["today_visits"] >= 2
    assert current["last_visit_at"]


def test_ensure_minimum_total_restores_counter(tmp_path):
    stats_file = tmp_path / "visitor_stats.json"
    record_visit(stats_file)

    restored = ensure_minimum_total(120, stats_file)
    current = visitor_stats(stats_file)

    assert restored["total_visits"] >= 120
    assert current["total_visits"] >= 120
