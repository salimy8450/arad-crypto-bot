"""Small SQLite persistence for personal watchlists and alert de-duplication."""
import sqlite3
from pathlib import Path

DB_PATH = Path("arad_meme_hunter.db")

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS watchlist (
        chain TEXT NOT NULL, contract_address TEXT NOT NULL, name TEXT, symbol TEXT,
        added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(chain, contract_address))""")
    db.execute("""CREATE TABLE IF NOT EXISTS sent_alerts (
        chain TEXT NOT NULL, contract_address TEXT NOT NULL, alert_type TEXT NOT NULL,
        sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(chain, contract_address, alert_type))""")
    db.commit()
    return db

def list_watchlist():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM watchlist ORDER BY added_at DESC")]

def add_watch(chain, address, name="", symbol=""):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO watchlist(chain,contract_address,name,symbol) VALUES(?,?,?,?)",
                   (chain.lower(), address, name, symbol))

def remove_watch(chain, address):
    with connect() as db:
        cur = db.execute("DELETE FROM watchlist WHERE chain=? AND contract_address=?", (chain.lower(), address))
        return cur.rowcount > 0

def alert_seen(chain, address, alert_type="strong"):
    with connect() as db:
        row = db.execute("SELECT 1 FROM sent_alerts WHERE chain=? AND contract_address=? AND alert_type=?",
                         (chain, address, alert_type)).fetchone()
        return row is not None

def mark_alert(chain, address, alert_type="strong"):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO sent_alerts(chain,contract_address,alert_type) VALUES(?,?,?)",
                   (chain, address, alert_type))
