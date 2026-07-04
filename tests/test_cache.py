from app.cache import empty_cache, load_cache, save_cache
from app.services import PredictionService
import time


def test_cache_roundtrip(tmp_path):
    path = tmp_path / "cache.json"
    payload = empty_cache()
    payload["generated_at"] = "2026-06-03T00:00:00+00:00"
    payload["matches"] = [{"id": "wc2026-001"}]
    save_cache(payload, path)
    loaded = load_cache(path)
    assert loaded["generated_at"] == payload["generated_at"]
    assert loaded["matches"][0]["id"] == "wc2026-001"


def test_auto_sync_returns_cache_and_finishes_in_background(monkeypatch):
    service = PredictionService()
    old_cache = {"matches": [{"id": "wc2026-001"}], "summary": {}, "generated_at": "old"}
    saved = []

    def fake_sync(cache, include_technical=True):
        assert include_technical is False
        time.sleep(0.02)
        updated = dict(cache)
        updated["generated_at"] = "new"
        updated["summary"] = {"live_result_synced_at": "new"}
        return updated

    monkeypatch.setattr("app.services.load_cache", lambda: old_cache)
    monkeypatch.setattr("app.services.save_cache", lambda payload: saved.append(payload))
    monkeypatch.setattr("app.services.sync_live_results", fake_sync)

    returned = service._cache_with_auto_sync()
    assert returned is old_cache
    assert service._task_snapshot()["running"] is True

    for _ in range(20):
        if saved:
            break
        time.sleep(0.01)
    assert saved[0]["generated_at"] == "new"
    assert service._task_snapshot()["running"] is False


def test_force_sync_starts_even_when_cache_is_fresh(monkeypatch):
    service = PredictionService()
    fresh_cache = {
        "matches": [{"id": "wc2026-001"}],
        "summary": {"live_result_synced_at": "2999-01-01T00:00:00+00:00"},
        "generated_at": "fresh",
    }
    saved = []

    def fake_sync(cache, include_technical=True):
        assert include_technical is False
        updated = dict(cache)
        updated["generated_at"] = "forced"
        return updated

    monkeypatch.setattr("app.services.load_cache", lambda: fresh_cache)
    monkeypatch.setattr("app.services.save_cache", lambda payload: saved.append(payload))
    monkeypatch.setattr("app.services.sync_live_results", fake_sync)

    returned = service._cache_with_auto_sync(force_sync=True)
    assert returned is fresh_cache

    for _ in range(20):
        if saved:
            break
        time.sleep(0.01)
    assert saved[0]["generated_at"] == "forced"
