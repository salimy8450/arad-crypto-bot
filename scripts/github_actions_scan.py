import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from app.scanner import DexScanner
from app.scoring import score_market

MAX_CAP = float(os.getenv("MAX_MARKET_CAP_USD", "500000"))
MIN_LIQ = float(os.getenv("MIN_LIQUIDITY_USD", "50000"))
THRESHOLD = float(os.getenv("STRONG_PUMP_SCORE", "7.5"))
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STATE = Path("data/alert_state.json")
PUBLIC_DATA = Path("docs/data/tokens.json")

def score_row(row):
    pair = {
        "volume": {"h24": row.get("volume_24h_usd")},
        "liquidity": {"usd": row.get("liquidity_usd")},
        "txns": {"h24": {"buys": row.get("buys_24h"), "sells": row.get("sells_24h")}},
        "priceChange": {"h24": row.get("change_24h_pct")},
    }
    result = score_market(pair)
    return {**row, "pump_score": result.pump_score, "status": result.status,
            "reasons": result.reasons, "listing_score": None,
            "ourbit_status": "UNKNOWN", "security_status": "NOT_VERIFIED"}

def read_state():
    try:
        return set(json.loads(STATE.read_text()).get("sent", []))
    except (OSError, ValueError, TypeError):
        return set()

async def notify(client, row):
    message = (
        "⚡ ARAD MEME HUNTER — STRONG MOMENTUM\n"
        f"{row.get('name')} ({row.get('symbol')})\n"
        f"Network: {row.get('chain')} | Score: {row['pump_score']}/10\n"
        f"Market cap/FDV: ${float(row.get('market_cap_usd') or row.get('fdv_usd') or 0):,.0f}\n"
        f"Liquidity: ${float(row.get('liquidity_usd') or 0):,.0f}\n"
        "Orbit listing: UNKNOWN | Contract security: UNVERIFIED\n"
        f"Contract: {row.get('contract_address')}\n"
        f"{row.get('dex_url') or ''}\n"
        "PAPER MODE — no trade executed."
    )
    response = await client.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message[:3900], "disable_web_page_preview": True},
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError("Telegram rejected sendMessage")

async def main():
    scanner = DexScanner("https://api.dexscreener.com", MAX_CAP, MIN_LIQ)
    raw = await scanner.scan(force=True)
    rows = [score_row(r) for r in raw]
    rows.sort(key=lambda r: r["pump_score"], reverse=True)
    PUBLIC_DATA.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows), "threshold": THRESHOLD, "paper_mode": True,
        "notice": "Momentum ranking only; Orbit listing and contract security are unverified.",
        "tokens": rows[:300],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    sent = read_state()
    new_sent = set(sent)
    alerts = [r for r in rows if r["pump_score"] >= THRESHOLD
              and f"{r['chain']}:{r['contract_address']}" not in sent]
    if TOKEN and CHAT_ID and alerts:
        async with httpx.AsyncClient(timeout=20) as client:
            for row in alerts[:8]:
                await notify(client, row)
                new_sent.add(f"{row['chain']}:{row['contract_address']}")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"sent": sorted(new_sent)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Scanned {len(rows)} live pairs; {len(alerts)} new strong candidates; Telegram configured={bool(TOKEN and CHAT_ID)}")

if __name__ == "__main__":
    asyncio.run(main())
