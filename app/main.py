import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .scanner import DexScanner
from .scoring import score_market
from .notifier import send_telegram, set_webhook
from .mock_data import mock_tokens
from .storage import list_watchlist, add_watch, remove_watch, alert_seen, mark_alert

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("arad")

class Settings(BaseSettings):
    app_name: str = "ARAD MEME HUNTER PRO"
    max_market_cap_usd: float = 500000
    min_liquidity_usd: float = 50000
    strong_pump_score: float = 7.5
    scan_interval_seconds: int = 300
    dexscreener_base_url: str = "https://api.dexscreener.com"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_secret: str = ""
    app_base_url: str = ""
    mock_data_enabled: bool = True
    admin_api_token: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

cfg = Settings()
scanner = DexScanner(cfg.dexscreener_base_url, cfg.max_market_cap_usd, cfg.min_liquidity_usd)

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
        if rows:
            return [enrich(r) for r in rows]
    except Exception:
        log.exception("DexScreener scan failed")
        if not cfg.mock_data_enabled:
            raise
    if cfg.mock_data_enabled:
        return [enrich(r) for r in mock_tokens()]
    return []

async def send_strong_alerts():
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        return 0
    rows = await get_rows(True)
    sent = 0
    for r in rows:
        if r.get("is_mock") or r["pump_score"] < cfg.strong_pump_score:
            continue
        if alert_seen(r["chain"], r["contract_address"]):
            continue
        msg = (
            f"⚡ ARAD MEME HUNTER — STRONG MOMENTUM\\n"
            f"{r['name']} ({r['symbol']})\\n"
            f"Network: {r['chain']} | Pump score: {r['pump_score']}/10\\n"
            f"Market cap/FDV: ${float(r.get('market_cap_usd') or r.get('fdv_usd') or 0):,.0f}\\n"
            f"Liquidity: ${float(r.get('liquidity_usd') or 0):,.0f}\\n"
            f"Orbit listing: UNKNOWN | Contract security: UNVERIFIED\\n"
            f"Contract: {r['contract_address']}\\n"
            f"Data: DexScreener | PAPER MODE — no trade executed."
        )
        try:
            if await send_telegram(cfg.telegram_bot_token, cfg.telegram_chat_id, msg):
                mark_alert(r["chain"], r["contract_address"])
                sent += 1
        except Exception:
            log.exception("Telegram alert failed for %s", r.get("symbol"))
    return sent

async def alert_loop():
    while True:
        try:
            await send_strong_alerts()
        except Exception:
            log.exception("Scheduled alert scan failed")
        await asyncio.sleep(max(60, cfg.scan_interval_seconds))

async def handle_telegram_update(update: dict):
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    # Only the explicitly configured chat is allowed to control this bot.
    if not cfg.telegram_chat_id or chat_id != str(cfg.telegram_chat_id):
        log.warning("Ignored Telegram update from an unapproved chat")
        return
    text = (message.get("text") or "").strip()
    command = text.split()[0].split("@")[0].lower() if text else ""
    if command in {"/start", "/help"}:
        reply = ("سلام! ربات ARAD MEME HUNTER فعال است.\\n"
                 "/list — نمایش کاندیداهای قوی\\n"
                 "/watchlist — نمایش واچ‌لیست\\n"
                 "/alert — اجرای اسکن هشدار فوری\\n"
                 "حالت PAPER است؛ هیچ معامله‌ای انجام نمی‌شود.")
    elif command == "/list":
        rows = await get_rows()
        rows = [r for r in rows if not r.get("is_mock") and r["pump_score"] >= cfg.strong_pump_score]
        rows = sorted(rows, key=lambda x: x["pump_score"], reverse=True)[:10]
        reply = "کاندیداهای قوی فعلی:\\n" + ("\\n".join(
            f"• {r['symbol']} ({r['chain']}) — {r['pump_score']}/10 — ${float(r.get('market_cap_usd') or r.get('fdv_usd') or 0):,.0f}"
            for r in rows) if rows else "فعلاً کاندیدای زنده‌ای از آستانه عبور نکرده است.")
    elif command == "/watchlist":
        items = list_watchlist()[:20]
        reply = "واچ‌لیست:\\n" + ("\\n".join(
            f"• {x.get('symbol') or x.get('name') or 'Token'} — {x['chain']} — {x['contract_address']}"
            for x in items) if items else "واچ‌لیست خالی است.")
    elif command == "/alert":
        count = await send_strong_alerts()
        reply = f"اسکن انجام شد. تعداد هشدارهای جدید ارسال‌شده: {count}."
    else:
        reply = "دستور ناشناخته است. /start را بفرست."
    await send_telegram(cfg.telegram_bot_token, chat_id, reply)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if cfg.telegram_bot_token and cfg.telegram_chat_id and cfg.app_base_url:
        try:
            webhook_url = cfg.app_base_url.rstrip("/") + "/telegram/webhook"
            await set_webhook(cfg.telegram_bot_token, webhook_url, cfg.telegram_webhook_secret)
            log.info("Telegram webhook configured")
        except Exception:
            log.exception("Could not configure Telegram webhook")
    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        task = asyncio.create_task(alert_loop())
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(title=cfg.app_name, version="1.1.0", description="Read-only meme-token discovery dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="dashboard"), name="static")

class WatchRequest(BaseModel):
    chain: str
    contract_address: str = Field(min_length=3, max_length=128)
    name: str = ""
    symbol: str = ""

@app.get("/", response_class=HTMLResponse)
async def home():
    return Path("dashboard/index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():
    return {"status":"ok","paper_mode":True,"mock_data_enabled":cfg.mock_data_enabled,
            "telegram_configured":bool(cfg.telegram_bot_token and cfg.telegram_chat_id),
            "telegram_webhook_configured":bool(cfg.app_base_url and cfg.telegram_webhook_secret),
            "chains":["solana","base","bsc","ethereum"],"provider":"DexScreener"}

@app.get("/api/tokens")
async def tokens(force:bool=False, chain:str|None=None, sort:str=Query("pump_score"),
                 q:str|None=None, min_score:float=0):
    try:
        rows = await get_rows(force)
    except Exception as exc:
        raise HTTPException(502, detail=f"Market provider error: {type(exc).__name__}")
    if chain:
        rows=[r for r in rows if r["chain"]==chain.lower()]
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
            return {**r,"analysis":{"entry_reference":price or None,
                "stop_reference":round(price*.97,12) if price else None,
                "targets":[round(price*1.05,12),round(price*1.10,12),round(price*1.18,12)] if price else [],
                "method":"Illustrative percentage levels only; not chart-derived technical signals",
                "risk_notes":["قرارداد و مالکیت توکن مستقل بررسی نشده است",
                    "وضعیت قفل نقدینگی و تمرکز هولدرها نامشخص است",
                    "لیست‌شدن در اوربیت تأیید نشده است","میم‌کوین‌ها ممکن است تمام ارزش خود را از دست بدهند"]}}
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
    if not remove_watch(chain,address):
        raise HTTPException(404,"Watchlist item not found")
    return {"deleted":True}

@app.post("/api/alerts/test")
async def test_alert(x_admin_token: str|None=Header(default=None)):
    if cfg.admin_api_token and not hmac.compare_digest(x_admin_token or "", cfg.admin_api_token):
        raise HTTPException(401,"Admin token required")
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        raise HTTPException(400,"Telegram is not configured")
    ok=await send_telegram(cfg.telegram_bot_token,cfg.telegram_chat_id,
        "ARAD MEME HUNTER PRO: Telegram connection test. PAPER MODE; no trade executed.")
    return {"sent":bool(ok)}

@app.post("/api/alerts/scan")
async def alert_scan(x_admin_token: str|None=Header(default=None)):
    if cfg.admin_api_token and not hmac.compare_digest(x_admin_token or "", cfg.admin_api_token):
        raise HTTPException(401,"Admin token required")
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        raise HTTPException(400,"Telegram is not configured")
    count=await send_strong_alerts()
    return {"alerts_sent":count,"paper_mode":True}

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str|None=Header(default=None)):
    if not cfg.telegram_bot_token or not cfg.telegram_webhook_secret:
        raise HTTPException(503,"Telegram webhook is not configured")
    if not hmac.compare_digest(x_telegram_bot_api_secret_token or "",cfg.telegram_webhook_secret):
        raise HTTPException(403,"Invalid Telegram webhook secret")
    update=await request.json()
    await handle_telegram_update(update)
    return {"ok":True}
