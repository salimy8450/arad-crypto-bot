import asyncio
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone

import httpx

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STATE = Path("data/ourbit_listing_state.json")
CHANNEL = "https://t.me/s/ourbitofficial"

class ChannelParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.posts = []
        self.current = None
        self.text_depth = 0
        self.anchor_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        post_id = attrs.get("data-post")
        if post_id and post_id.startswith("ourbitofficial/"):
            if self.current:
                self.posts.append(self.current)
            self.current = {"id": post_id.rsplit("/", 1)[-1], "text": [], "links": []}
            self.text_depth = 0
        if self.current and tag == "div" and "tgme_widget_message_text" in classes:
            self.text_depth += 1
        if self.current and tag == "a":
            self.anchor_depth += 1
            href = attrs.get("href")
            if href:
                self.current["links"].append(href)

    def handle_endtag(self, tag):
        if self.current and tag == "div" and self.text_depth:
            self.text_depth -= 1
        if self.current and tag == "a" and self.anchor_depth:
            self.anchor_depth -= 1

    def handle_data(self, data):
        if self.current and self.text_depth:
            self.current["text"].append(data)

    def close(self):
        super().close()
        if self.current:
            self.posts.append(self.current)
            self.current = None

def is_listing(text):
    t = re.sub(r"\s+", " ", text).lower()
    if any(x in t for x in ("delist", "delisting", "will remove", "suspend trading")):
        return False
    patterns = (
        "will list", "to be listed on ourbit", "new listing",
        "listing on ourbit", "ready for the launch", "will be listed",
    )
    return any(p in t for p in patterns)

def read_state():
    try:
        return set(json.loads(STATE.read_text(encoding="utf-8")).get("sent_posts", []))
    except (OSError, ValueError, TypeError):
        return set()

async def main():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ARADListingRadar/1.0)"}
    async with httpx.AsyncClient(timeout=25, headers=headers, follow_redirects=True) as client:
        response = await client.get(CHANNEL)
        response.raise_for_status()
        parser = ChannelParser()
        parser.feed(response.text)
        parser.close()

        sent = read_state()
        fresh = []
        for post in parser.posts:
            post_id = post["id"]
            text = re.sub(r"\s+", " ", " ".join(post["text"])).strip()
            if not post_id or post_id in sent or not is_listing(text):
                continue
            official_links = [u for u in post["links"] if "ourbit.com/" in u]
            ticker_match = re.search(r"\$([A-Z0-9]{2,15})", text)
            ticker = ticker_match.group(1) if ticker_match else "در متن مشخص نیست"
            kind = "Futures" if "futures" in text.lower() or "perpetual" in text.lower() else "Spot / Listing"
            source = official_links[0] if official_links else f"https://t.me/ourbitofficial/{post_id}"
            fresh.append((post_id, text, ticker, kind, source))

        if TOKEN and CHAT_ID and fresh:
            for post_id, text, ticker, kind, source in fresh:
                message = (
                    "🚨 ARAD — OURBIT OFFICIAL LISTING ALERT\n"
                    f"نماد: {ticker}\n"
                    f"نوع اطلاعیه: {kind}\n"
                    "وضعیت: اطلاعیه در کانال رسمی Ourbit شناسایی شد\n\n"
                    f"{text[:1800]}\n\n"
                    f"منبع رسمی: {source}\n"
                    "توجه: این هشدار خبر لیست‌شدن است، نه سیگنال خرید."
                )
                resp = await client.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": CHAT_ID, "text": message[:3900], "disable_web_page_preview": True},
                )
                resp.raise_for_status()
                if not resp.json().get("ok"):
                    raise RuntimeError("Telegram rejected Ourbit listing alert")
                sent.add(post_id)

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({
        "sent_posts": sorted(sent),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": CHANNEL,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ourbit official channel checked: {len(parser.posts)} posts; {len(fresh)} new listing notices; Telegram configured={bool(TOKEN and CHAT_ID)}")

if __name__ == "__main__":
    asyncio.run(main())
