import httpx

async def send_telegram(token: str, chat_id: str, message: str) -> bool:
    if not token or not chat_id: return False
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat_id,'text':message,'disable_web_page_preview':True})
        r.raise_for_status(); return bool(r.json().get('ok'))
