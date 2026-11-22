import app.storage as storage

def test_watchlist_and_alert_deduplication(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.add_watch("solana", "So11111111111111111111111111111111111111112", "Demo", "DEMO")
    items = storage.list_watchlist()
    assert len(items) == 1
    assert items[0]["symbol"] == "DEMO"
    assert not storage.alert_seen("solana", "So11111111111111111111111111111111111111112")
    storage.mark_alert("solana", "So11111111111111111111111111111111111111112")
    assert storage.alert_seen("solana", "So11111111111111111111111111111111111111112")
    assert storage.remove_watch("solana", "So11111111111111111111111111111111111111112")
    assert storage.list_watchlist() == []
