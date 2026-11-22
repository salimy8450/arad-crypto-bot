# ARAD MEME HUNTER PRO

سامانه‌ی کشف و پایش توکن‌های پرریسک با تمرکز بر میم‌کوین‌ها؛ در این نسخه تمام عملیات **فقط خواندنی (Paper Mode)** است و هیچ کیف‌پول، امضای تراکنش یا سفارش معاملاتی وجود ندارد.

## فناوری و معماری
- Python 3.11+ و FastAPI برای API و سرویس وب
- داشبورد واکنش‌گرا با HTML/CSS/JavaScript بدون نیاز به build frontend
- DexScreener API برای کشف اولیه جفت‌ارزها و داده بازار
- SQLite برای Watchlist و جلوگیری از هشدار تکراری
- Telegram Bot API برای ارسال هشدار اختیاری
- pytest برای تست امتیازدهی

## قابلیت‌های فعلی
- شبکه‌های Solana، Base، BNB Chain و Ethereum
- سقف مارکت‌کپ/FDV برابر 500,000 دلار و حداقل نقدینگی 50,000 دلار
- جستجو با نام، نماد یا آدرس قرارداد
- مرتب‌سازی بر اساس امتیاز مومنتوم، حجم، مارکت‌کپ، نقدینگی و تغییر قیمت
- صفحه جزئیات API هر توکن، Watchlist پایدار و حذف از Watchlist
- هشدار تلگرام برای امتیاز مومنتوم قوی، همراه با برچسب صریح «اوربیت/امنیت تأیید نشده»
- داده Mock برای آزمایش رابط در زمان قطع API
- مستندات API در مسیر /docs

## نکته مهم درباره امتیازها
**Pump Score** یک رتبه‌بندی شفاف مبتنی بر نسبت حجم به نقدینگی، نسبت خرید/فروش، تغییر قیمت و نقدینگی است؛ احتمال آماری سود یا پامپ نیست.
**Orbit Listing Score در این نسخه عمداً null است** چون دیتاست تاریخی و منبع رسمی قابل‌اتکا برای پذیرش/لیست‌شدن اوربیت متصل نشده است. هیچ عدد ساختگی به‌عنوان احتمال لیست‌شدن نمایش داده نمی‌شود.
داده‌ی DexScreener نیز به‌تنهایی اثبات نمی‌کند یک توکن واقعاً میم‌کوین است. فهرست فعلی «کاندیدای کشف» است و برای طبقه‌بندی قطعی میم‌کوین، تحلیل متادیتا و منابع اجتماعی باید اضافه شود.
سطوح ورود/حدضرر/تارگت در API جزئیات صرفاً محاسبات نمونه بر اساس درصد قیمت هستند، نه سطوح تکنیکال حاصل از کندل‌ها؛ در UI باید با همین هشدار نمایش داده شوند.
امنیت قرارداد، قفل نقدینگی، تمرکز هولدرها و وضعیت لیست‌شدن در اوربیت در این نسخه تأیید نشده‌اند.

## نصب و اجرای لوکال
نیازمندی: Python 3.11 یا جدیدتر و Git.

```bash
git clone https://github.com/salimy8450/arad-crypto-bot.git
cd arad-crypto-bot
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

سپس داشبورد: http://127.0.0.1:8000
مستندات API: http://127.0.0.1:8000/docs

### حالت Mock
در فایل .env مقدار `MOCK_DATA_ENABLED=true` را قرار دهید. اگر API در دسترس نباشد یا داده‌ای برنگرداند، نمونه‌های ساختگی با برچسب MOCK نمایش داده می‌شوند. این نمونه‌ها قیمت واقعی نیستند.

## تنظیم Telegram
1. در تلگرام با BotFather یک ربات بسازید.
2. توکن را فقط در متغیر محیطی سرور قرار دهید؛ آن را در GitHub عمومی یا گفتگو منتشر نکنید.
3. مقدار `TELEGRAM_BOT_TOKEN` و `TELEGRAM_CHAT_ID` را تنظیم کنید.
4. سرور را مجدداً اجرا کنید.
5. از `POST /api/alerts/test` برای تست و `POST /api/alerts/scan` برای اسکن هشدارها استفاده کنید.

## متغیرهای محیطی
| متغیر | پیش‌فرض | کاربرد |
|---|---:|---|
| MAX_MARKET_CAP_USD | 500000 | سقف مارکت‌کپ/FDV |
| MIN_LIQUIDITY_USD | 50000 | حداقل نقدینگی |
| STRONG_PUMP_SCORE | 7.5 | حد هشدار قوی از 10 |
| DEXSCREENER_BASE_URL | https://api.dexscreener.com | API بازار |
| MOCK_DATA_ENABLED | true | فعال‌سازی داده آزمایشی |
| TELEGRAM_BOT_TOKEN | خالی | توکن ربات |
| TELEGRAM_CHAT_ID | خالی | شناسه چت |

## API
- `GET /api/health` وضعیت سرویس
- `GET /api/tokens?sort=pump_score&chain=solana&q=doge&min_score=5` فهرست و فیلتر
- `GET /api/tokens/{chain}/{address}` جزئیات
- `GET /api/search?q=token` جستجو
- `GET /api/watchlist` مشاهده Watchlist
- `POST /api/watchlist` افزودن: JSON شامل chain، contract_address، name و symbol
- `DELETE /api/watchlist/{chain}/{address}` حذف
- `POST /api/alerts/test` تست تلگرام
- `POST /api/alerts/scan` اسکن و ارسال هشدارهای قوی

## تست
```bash
pip install pytest
pytest -q
```

## دیپلوی روی Render
1. مخزن را به Render متصل کنید.
2. یک Web Service از نوع Python بسازید.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. متغیرهای محیطی بالا را در بخش Environment وارد کنید.
6. برای ذخیره پایدار SQLite در Render باید دیسک پایدار متصل و مسیر DB به volume منتقل شود؛ در غیر این صورت Watchlist ممکن است پس از redeploy از بین برود. برای استفاده چندکاربره، PostgreSQL توصیه می‌شود.

## دیپلوی روی Vercel
این پروژه FastAPI/SQLite و یک فرایند وب دائمی دارد؛ بنابراین Vercel انتخاب ساده‌ای برای این نسخه نیست. Render یا Railway مناسب‌تر است. برای Vercel باید backend به serverless functions و ذخیره‌سازی به دیتابیس مدیریت‌شده منتقل شود.

## محدودیت‌ها و ریسک‌ها
- فید DexScreener، همه توکن‌های موجود را پوشش نمی‌دهد و توکن‌های جدید یا کم‌نمایش ممکن است از قلم بیفتند.
- در صورت نبود marketCap از FDV به‌عنوان proxy استفاده می‌شود و در پاسخ مشخص است.
- API عمومی و rate limit ممکن است باعث تأخیر یا خطا شود.
- برای استفاده واقعی، اتصال منبع امنیت قرارداد (مانند ارائه‌دهنده معتبر برای هر شبکه)، داده هولدرها، تاریخچه کندل، منبع رسمی اوربیت و پایش اجتماعی ضروری است.
- هیچ امتیازی تضمین‌کننده رشد، لیست‌شدن یا سود نیست. میم‌کوین‌ها می‌توانند تمام ارزش خود را از دست بدهند.

## وضعیت
این نسخه یک MVP اجرایی با داشبورد، API، داده آزمایشی، Watchlist و هشدار تلگرام است؛ اما هنوز محصول کاملِ اعتبارسنجی‌شده برای پیش‌بینی لیست‌شدن اوربیت یا ارزیابی امنیت قرارداد نیست.
