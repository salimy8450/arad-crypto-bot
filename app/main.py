from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic_settings import BaseSettings, SettingsConfigDict
from .scanner import DexScanner
from .scoring import score_market
from .notifier import send_telegram

class Settings(BaseSettings):
    app_name: str = 'ARAD MEME HUNTER PRO'
    max_market_cap_usd: float = 500000
    min_liquidity_usd: float = 50000
    strong_pump_score: float = 7.5
    dexscreener_base_url: str = 'https://api.dexscreener.com'
    telegram_bot_token: str = ''
    telegram_chat_id: str = ''
    paper_mode: bool = True
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

cfg=Settings()
scanner=DexScanner(cfg.dexscreener_base_url,cfg.max_market_cap_usd,cfg.min_liquidity_usd)
app=FastAPI(title=cfg.app_name,version='0.1.0')
app.mount('/static',StaticFiles(directory='dashboard'),name='static')

def as_pair(r):
    return {'volume':{'h24':r.get('volume_24h_usd')},'liquidity':{'usd':r.get('liquidity_usd')},'txns':{'h24':{'buys':r.get('buys_24h'),'sells':r.get('sells_24h')}},'priceChange':{'h24':r.get('change_24h_pct')}}

@app.get('/',response_class=HTMLResponse)
async def home(): return Path('dashboard/index.html').read_text(encoding='utf-8')

@app.get('/api/health')
async def health(): return {'status':'ok','paper_mode':True,'chains':['solana','base','bsc','ethereum']}

@app.get('/api/tokens')
async def tokens(force:bool=False,chain:str|None=None,sort:str=Query('pump_score')):
    try: rows=await scanner.scan(force)
    except Exception as exc: raise HTTPException(502,detail=f'Market provider error: {type(exc).__name__}')
    out=[]
    for r in rows:
        s=score_market(as_pair(r)); out.append({**r,'pump_score':s.pump_score,'listing_score':s.listing_score,'status':s.status,'reasons':s.reasons,'security_status':'NOT_VERIFIED','ourbit_status':'NOT_VERIFIED'})
    if chain: out=[r for r in out if r['chain']==chain.lower()]
    key={'volume':lambda r:float(r.get('volume_24h_usd') or 0),'market_cap':lambda r:float(r.get('market_cap_usd') or r.get('fdv_usd') or 0),'pump_score':lambda r:r['pump_score']}.get(sort,lambda r:r['pump_score'])
    out.sort(key=key,reverse=sort!='market_cap')
    return {'count':len(out),'filters':{'max_market_cap_usd':cfg.max_market_cap_usd,'min_liquidity_usd':cfg.min_liquidity_usd},'paper_mode':True,'tokens':out}

@app.get('/api/search')
async def search(q:str):
    q=q.strip().lower()
    if not q:return {'tokens':[]}
    rows=await scanner.scan()
    return {'tokens':[r for r in rows if q in r['name'].lower() or q in r['symbol'].lower() or q in r['contract_address'].lower()][:30]}

@app.post('/api/alerts/test')
async def test_alert():
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id: raise HTTPException(400,'Set Telegram secrets first')
    return {'sent':await send_telegram(cfg.telegram_bot_token,cfg.telegram_chat_id,'ARAD MEME HUNTER: Telegram test. PAPER MODE; no trade executed.')}

@app.post('/api/alerts/scan')
async def alert_scan():
    rows=await scanner.scan(True); sent=[]
    for r in rows:
        s=score_market(as_pair(r))
        # Strict gate: market momentum alone is not enough for a pre-listing alert.
        # Until verified security + official Ourbit evidence providers are connected, suppress alerts.
        security_verified_safe = False
        official_ourbit_evidence = False
        if s.pump_score>=cfg.strong_pump_score and security_verified_safe and official_ourbit_evidence and cfg.telegram_bot_token and cfg.telegram_chat_id:
            msg=f"ARAD MEME HUNTER | STRONG MARKET WATCH\\n{r['name']} ({r['symbol']})\\nChain: {r['chain']}\\nPump: {s.pump_score}/10\\nOurbit: NOT VERIFIED\\nLiquidity: ${r['liquidity_usd']:,.0f}\\nContract: {r['contract_address']}\\nPAPER MODE - no trade"
            if await send_telegram(cfg.telegram_bot_token,cfg.telegram_chat_id,msg): sent.append(r['contract_address'])
    return {'alerts_sent':len(sent),'contracts':sent,'paper_mode':True}
