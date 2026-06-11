from app.cache import empty_cache, load_cache, save_cache


def test_cache_roundtrip(tmp_path):
    path = tmp_path / "cache.json"
    payload = empty_cache()
    payload["generated_at"] = "2026-06-03T00:00:00+00:00"
    payload["matches"] = [{"id": "wc2026-001"}]
    save_cache(payload, path)
    loaded = load_cache(path)
    assert loaded["generated_at"] == payload["generated_at"]
    assert loaded["matches"][0]["id"] == "wc2026-001"

