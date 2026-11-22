from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from .scanner import DexScanner
from .scoring import score_market
from .notifier import send_telegram
from .mock_data import mock_tokens
from .storage import list_watchlist, add_watch, remove_watch, alert_seen, mark_alert

class Settings(BaseSettings):
    app_name: str = "ARAD MEME HUNTER PRO"
    max_market_cap_usd: float = 500000
    min_liquidity_usd: float = 50000
    strong_pump_score: float = 7.5
    dexscreener_base_url: str = "https://api.dexscreener.com"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    mock_data_enabled: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

cfg = Settings()
scanner = DexScanner(cfg.dexscreener_base_url, cfg.max_market_cap_usd, cfg.min_liquidity_usd)
app = FastAPI(title=cfg.app_name, version="1.0.0", description="Read-only meme-token discovery dashboard")
app.mount("/static", StaticFiles(directory="dashboard"), name="static")

class WatchRequest(BaseModel):
    chain: str
    contract_address: str = Field(min_length=3, max_length=128)
    name: str = ""
    symbol: str = ""

def as_pair(r):
    return {"volume":{"h24":r.get("volume_24h_usd")},
            "liquidity":{"usd":r.get("liquidity_usd")},
            "txns":{"h24":{"buys":r.get("buys_24h"),"sells":r.get("sells_24h")}},
            "priceChange":{"h24":r.get("change_24h_pct")}}

def enrich(r):
    s = score_market(as_pair(r))
    return {**r, "pump_score":s.pump_score, "listing_score":s.listing_score,
            "status":s.status, "reasons":s.reasons,
            "security_status":"NOT_VERIFIED", "ourbit_status":"NOT_VERIFIED",
            "is_mock":bool(r.get("is_mock", False))}

async def get_rows(force=False):
    try:
        rows = await scanner.scan(force)
        if rows: return [enrich(r) for r in rows]
    except Exception:
        if not cfg.mock_data_enabled: raise
    if cfg.mock_data_enabled:
        return [enrich(r) for r in mock_tokens()]
    return []

@app.get("/", response_class=HTMLResponse)
async def home():
    return Path("dashboard/index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():
    return {"status":"ok","paper_mode":True,"mock_data_enabled":cfg.mock_data_enabled,
            "chains":["solana","base","bsc","ethereum"],"provider":"DexScreener"}

@app.get("/api/tokens")
async def tokens(force:bool=False, chain:str|None=None, sort:str=Query("pump_score"),
                 q:str|None=None, min_score:float=0):
    try: rows = await get_rows(force)
    except Exception as exc: raise HTTPException(502, detail=f"Market provider error: {type(exc).__name__}")
    if chain: rows=[r for r in rows if r["chain"]==chain.lower()]
    if q:
        q=q.lower().strip()
        rows=[r for r in rows if q in r["name"].lower() or q in r["symbol"].lower() or q in r["contract_address"].lower()]
    rows=[r for r in rows if r["pump_score"]>=min_score]
    sorters={"volume":lambda r:float(r.get("volume_24h_usd") or 0),
             "market_cap":lambda r:float(r.get("market_cap_usd") or r.get("fdv_usd") or 0),
             "liquidity":lambda r:float(r.get("liquidity_usd") or 0),
             "change":lambda r:float(r.get("change_24h_pct") or 0),
             "pump_score":lambda r:r["pump_score"]}
    rows.sort(key=sorters.get(sort,sorters["pump_score"]), reverse=sort!="market_cap")
    return {"count":len(rows),"filters":{"max_market_cap_usd":cfg.max_market_cap_usd,
            "min_liquidity_usd":cfg.min_liquidity_usd},"paper_mode":True,
            "data_mode":"MOCK" if rows and all(r["is_mock"] for r in rows) else "LIVE","tokens":rows}

@app.get("/api/tokens/{chain}/{address}")
async def token_detail(chain:str,address:str):
    rows=await get_rows()
    for r in rows:
        if r["chain"]==chain.lower() and r["contract_address"].lower()==address.lower():
            price=float(r.get("price_usd") or 0)
            # Indicative arithmetic levels only; not chart-derived trade signals.
            return {**r,"analysis":{"entry_reference":price or None,
                "stop_reference":round(price*.97,12) if price else None,
                "targets":[round(price*1.05,12),round(price*1.10,12),round(price*1.18,12)] if price else [],
                "method":"Illustrative ±3% risk / +5%, +10%, +18% targets; not technical levels",
                "risk_notes":["قرارداد و مالکیت توکن هنوز مستقل بررسی نشده است",
                    "وضعیت قفل نقدینگی و تمرکز هولدرها نامشخص است",
                    "لیست‌شدن در اوربیت تأیید نشده است","میم‌کوین‌ها ممکن است تمام سرمایه را از بین ببرند"]}}
    raise HTTPException(404,"Token not found in current scan")

@app.get("/api/search")
async def search(q:str):
    return {"tokens":[r for r in await get_rows() if q.lower() in r["name"].lower()
        or q.lower() in r["symbol"].lower() or q.lower() in r["contract_address"].lower()][:30]}

@app.get("/api/watchlist")
async def watchlist():
    return {"items":list_watchlist()}

@app.post("/api/watchlist")
async def watchlist_add(body:WatchRequest):
    if body.chain.lower() not in {"solana","base","bsc","ethereum"}:
        raise HTTPException(400,"Unsupported chain")
    add_watch(body.chain,body.contract_address,body.name,body.symbol)
    return {"saved":True,"items":list_watchlist()}

@app.delete("/api/watchlist/{chain}/{address}")
async def watchlist_delete(chain:str,address:str):
    if not remove_watch(chain,address): raise HTTPException(404,"Watchlist item not found")
    return {"deleted":True}

@app.post("/api/alerts/test")
async def test_alert():
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        raise HTTPException(400,"Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in hosting environment")
    ok=await send_telegram(cfg.telegram_bot_token,cfg.telegram_chat_id,
        "ARAD MEME HUNTER PRO: Telegram connection test. PAPER MODE; no trade executed.")
    return {"sent":bool(ok)}

@app.post("/api/alerts/scan")
async def alert_scan():
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        raise HTTPException(400,"Telegram is not configured")
    rows=await get_rows(True); sent=[]
    for r in rows:
        if r.get("is_mock") or r["pump_score"]<cfg.strong_pump_score or alert_seen(r["chain"],r["contract_address"]):
            continue
        msg=(f"⚡ ARAD STRONG MOMENTUM WATCH\\n{r['name']} ({r['symbol']})\\n"
             f"Network: {r['chain']}\\nPump score: {r['pump_score']}/10\\n"
             f"Market cap: ${float(r.get('market_cap_usd') or r.get('fdv_usd') or 0):,.0f}\\n"
             f"Liquidity: ${float(r.get('liquidity_usd') or 0):,.0f}\\n"
             f"Ourbit listing: UNVERIFIED | Contract security: UNVERIFIED\\n"
             f"{r['contract_address']}\\nPAPER MODE — no trade executed.")
        if await send_telegram(cfg.telegram_bot_token,cfg.telegram_chat_id,msg):
            mark_alert(r["chain"],r["contract_address"]); sent.append(r["contract_address"])
    return {"alerts_sent":len(sent),"contracts":sent,"paper_mode":True,
            "note":"Momentum alerts only; no claim of safety or Orbit listing probability."}
