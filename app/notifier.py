import httpx

TELEGRAM_API = "https://api.telegram.org"

async def telegram_call(token: str, method: str, payload: dict) -> dict:
    if not token:
        raise ValueError("Telegram bot token is missing")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{TELEGRAM_API}/bot{token}/{method}", json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API rejected {method}: {data}")
        return data

async def send_telegram(token: str, chat_id: str, message: str) -> bool:
    if not token or not chat_id:
        return False
    data = await telegram_call(token, "sendMessage", {
        "chat_id": chat_id, "text": message[:4000],
        "disable_web_page_preview": True
    })
    return bool(data.get("ok"))

async def set_webhook(token: str, webhook_url: str, secret: str) -> bool:
    if not token or not webhook_url or not secret:
        return False
    data = await telegram_call(token, "setWebhook", {
        "url": webhook_url,
        "secret_token": secret,
        "allowed_updates": ["message"],
        "drop_pending_updates": True
    })
    return bool(data.get("ok"))
