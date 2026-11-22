# ARAD MEME HUNTER PRO

سامانه پایش کاندیداهای توکن در شبکه‌های Solana، Base، BNB Chain و Ethereum. این پروژه **فقط خواندنی / Paper Mode** است و کیف‌پول، امضای تراکنش یا قابلیت خریدوفروش ندارد.

## معماری
- Python 3.12 + FastAPI
- داشبورد واکنش‌گرا HTML/CSS/JavaScript
- DexScreener API برای فید اولیه توکن‌ها و جفت‌ارزها
- SQLite برای واچ‌لیست و جلوگیری از هشدار تکراری
- Telegram Bot API از طریق Webhook امن
- اسکن خودکار هشدارها هر ۵ دقیقه (در زمان فعال بودن یک نمونه سرویس)
- Render Web Service + Persistent Disk

## وضعیت دقت و محدودیت تحلیل
- Pump Score از ۰ تا ۱۰ یک **رتبه‌بندی مومنتوم** مبتنی بر حجم/نقدینگی، نسبت خرید/فروش، تغییر قیمت و نقدینگی است؛ احتمال آماری سود یا پامپ نیست.
- Orbit Listing Score عمداً نامشخص است تا زمانی که داده تاریخی و معیارهای رسمی پذیرش اوربیت به سیستم متصل شوند. این نسخه ادعای پیش‌بینی احتمال لیست‌شدن نمی‌کند.
- DexScreener منبع جامع همه توکن‌ها نیست و داده آن به‌تنهایی میم‌کوین بودن یک پروژه را اثبات نمی‌کند.
- امنیت قرارداد، مالکیت، قفل نقدینگی، تمرکز هولدرها و لیست‌شدن اوربیت در این نسخه تأیید نمی‌شوند.
- سطوح ورود/حدضرر/تارگت موجود در جزئیات صرفاً محاسبات درصدی نمونه‌اند؛ سیگنال تکنیکال یا توصیه معامله نیستند.
- در Production مقدار MOCK_DATA_ENABLED=false قرار می‌گیرد تا داده ساختگی هرگز به‌جای بازار واقعی نمایش داده نشود.

## اجرای لوکال
نیازمند Python 3.11+ و Git:
```bash
git clone https://github.com/salimy8450/arad-crypto-bot.git
cd arad-crypto-bot
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
داشبورد: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/health

برای توسعه و نمایش نمونه‌ها، MOCK_DATA_ENABLED=true بماند. داده‌های نمونه با is_mock مشخص‌اند و هرگز برای تلگرام هشدار نمی‌شوند.

## متغیرهای محیطی

| نام | توضیح |
|---|---|
| MAX_MARKET_CAP_USD | سقف Market Cap/FDV؛ پیش‌فرض 500000 |
| MIN_LIQUIDITY_USD | حداقل نقدینگی؛ پیش‌فرض 50000 |
| STRONG_PUMP_SCORE | آستانه هشدار؛ پیش‌فرض 7.5 از 10 |
| SCAN_INTERVAL_SECONDS | فاصله اسکن خودکار؛ پیش‌فرض 300 ثانیه |
| DEXSCREENER_BASE_URL | آدرس API |
| MOCK_DATA_ENABLED | فقط در توسعه true؛ در Production false |
| ARAD_DB_PATH | مسیر فایل SQLite؛ در Render برابر /var/data/arad_meme_hunter.db |
| TELEGRAM_BOT_TOKEN | توکن محرمانه BotFather |
| TELEGRAM_CHAT_ID | شناسه عددی چت مجاز |
| APP_BASE_URL | آدرس عمومی HTTPS سرویس Render، بدون اسلش انتهایی |
| TELEGRAM_WEBHOOK_SECRET | راز وب‌هوک؛ در Render با generateValue ساخته می‌شود |
| ADMIN_API_TOKEN | رمز محافظ endpointهای مدیریتی؛ در Render خودکار ساخته می‌شود |

## ساخت ربات تلگرام
1. در تلگرام به @BotFather پیام بده.
2. دستور /newbot را بفرست، نام و username ربات را تعیین کن و توکن را دریافت کن.
3. توکن را فقط در Environment سرویس Render در کلید TELEGRAM_BOT_TOKEN وارد کن. توکن را در کد، GitHub یا گفتگو قرار نده.
4. از صفحه ربات Start را بزن تا اجازه دریافت پیام بدهی.
5. برای چت خصوصی، در تلگرام به @userinfobot پیام بده و عدد User ID را بردار؛ این عدد همان Chat ID گفت‌وگوی خصوصی با ربات است. آن را در TELEGRAM_CHAT_ID قرار بده. سپس حتماً وارد گفت‌وگوی ربات خودت شو و Start را بزن.
6. پس از تنظیم APP_BASE_URL و متغیرها، سرویس را redeploy کن. برنامه هنگام startup وب‌هوک HTTPS را با secret تنظیم می‌کند.
7. در تلگرام /start را بفرست.

دستورات:
- /start یا /help: راهنما
- /list: حداکثر ۱۰ کاندیدای زنده با امتیاز بالاتر از آستانه
- /watchlist: نمایش واچ‌لیست ذخیره‌شده در داشبورد
- /alert: اجرای اسکن فوری و ارسال هشدارهای تازه

ربات فقط به چتی پاسخ می‌دهد که شناسه آن در TELEGRAM_CHAT_ID تنظیم شده است. هشدار خودکار هر ۵ دقیقه اجرا می‌شود و هر قرارداد/نوع هشدار را فقط یک‌بار ثبت می‌کند. برای ارسال دوباره هشدارهای قبلی، رکوردهای جدول sent_alerts باید آگاهانه مدیریت شوند.

## دیپلوی روی Render با Blueprint
### پیش‌نیاز
- حساب GitHub با دسترسی به مخزن
- حساب Render
- توکن تلگرام و Chat ID (برای فعال‌سازی تلگرام)

### مراحل
1. مطمئن شو آخرین commitها در مخزن GitHub هستند.
2. وارد https://render.com شو و ثبت‌نام/ورود کن.
3. از Dashboard گزینه **New +** و سپس **Blueprint** را انتخاب کن.
4. مخزن `salimy8450/arad-crypto-bot` را متصل کن و دسترسی GitHub را تأیید کن.
5. Render فایل `render.yaml` را می‌خواند؛ سرویس `arad-meme-hunter-pro`، دیسک پایدار ۱ گیگابایتی و متغیرهای محیطی را نشان می‌دهد.
6. Blueprint را Apply کن. پلن Starter برای Persistent Disk در نظر گرفته شده و ممکن است هزینه داشته باشد؛ پیش از تأیید قیمت جاری Render را بررسی کن.
7. در Environment سرویس، این دو مقدار را وارد کن:
   - APP_BASE_URL = آدرس HTTPS سرویس، مانند https://نام-سرویس.onrender.com
   - TELEGRAM_BOT_TOKEN = توکن BotFather
   - TELEGRAM_CHAT_ID = شناسه عددی چت خودت
8. TELEGRAM_WEBHOOK_SECRET و ADMIN_API_TOKEN به‌صورت خودکار توسط Render ساخته می‌شوند؛ مقدار آن‌ها را عمومی نکن.
9. Save Changes و سپس Deploy latest commit را بزن.
10. وقتی Deploy موفق شد، آدرس `/api/health` را باز کن. باید status برابر ok و telegram_configured برابر true باشد.
11. داشبورد را در ریشه دامنه باز کن.

### دیپلوی دستی به‌جای Blueprint
- New + → Web Service → مخزن GitHub را انتخاب کن.
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`
- یک Persistent Disk با mount path برابر `/var/data` ایجاد کن.
- Environment Variables را طبق جدول بالا تنظیم کن.
- مقدار `ARAD_DB_PATH=/var/data/arad_meme_hunter.db` را حتماً تنظیم کن.

**SQLite و چند نمونه:** فقط یک نمونه از این سرویس را اجرا کن؛ SQLite برای چند replica هم‌زمان مناسب نیست. Persistent Disk در پلن‌های دارای پشتیبانی دیسک قابل استفاده است و ممکن است هزینه جداگانه داشته باشد. بدون دیسک پایدار، واچ‌لیست و تاریخچه جلوگیری از هشدار تکراری ممکن است با جایگزینی instance از بین برود.

## تست
```bash
pip install -r requirements-dev.txt
pytest -q
```
تست دستی پس از اجرا:
1. GET /api/health باید 200 بدهد.
2. GET / باید داشبورد را نمایش دهد.
3. GET /api/tokens در حالت توسعه باید داده MOCK یا LIVE با برچسب درست بدهد.
4. افزودن/حذف واچ‌لیست را از داشبورد امتحان کن.
5. /start، /list، /watchlist و /alert را در چت مجاز آزمایش کن.
6. بررسی کن پیام‌ها عبارت PAPER MODE و وضعیت UNKNOWN/UNVERIFIED را نشان دهند.
7. یک بار Deploy مجدد انجام بده و ماندگاری Watchlist را بررسی کن.

## مشکلات رایج
- **Application failed to start:** بررسی Build/Runtime Logs؛ مطمئن شو Start Command دقیق است و root directory ریشه مخزن است.
- **Static directory not found:** سرویس را از ریشه مخزن اجرا کن؛ dashboard باید در همان سطح app باشد.
- **SQLite readonly / no such directory:** مقدار ARAD_DB_PATH و mount path دیسک را بررسی کن.
- **Telegram webhook not configured:** APP_BASE_URL باید HTTPS و بدون / پایانی باشد؛ token و secret را بررسی و redeploy کن.
- **ربات به پیام پاسخ نمی‌دهد:** ابتدا Start را بزن، Chat ID را دقیق بررسی کن، سپس health را برای telegram_configured کنترل کن.
- **409 Conflict در Telegram:** یک webhook قدیمی یا polling هم‌زمان فعال است؛ این برنامه polling اجرا نمی‌کند، webhook قبلی را پاک کن و سرویس را restart کن.
- **هیچ توکنی دیده نمی‌شود:** MOCK_DATA_ENABLED=false در Production است؛ خطا یا محدودیت DexScreener را در Render Logs بررسی کن. داده ساختگی در Production عمداً غیرفعال است.
- **هشدار تکراری ارسال نمی‌شود:** جلوگیری از تکرار در SQLite فعال است؛ رکوردهای sent_alerts را فقط در صورت نیاز آگاهانه پاک کن.

## امنیت
- هیچ‌وقت توکن BotFather یا ADMIN_API_TOKEN را در GitHub commit نکن.
- فقط HTTPS را برای webhook به‌کار ببر.
- Chat ID مجاز در کد بررسی می‌شود.
- endpointهای مدیریتی /api/alerts/test و /api/alerts/scan با X-Admin-Token محافظت می‌شوند اگر ADMIN_API_TOKEN تنظیم شده باشد.
- این نسخه احراز هویت کاربران داشبورد ندارد؛ URL عمومی را خصوصی تلقی نکن و داده حساس ذخیره نکن.
- در صورت افشای Bot Token، از BotFather آن را revoke و تعویض کن.

## Endpointها
- GET /api/health
- GET /api/tokens
- GET /api/tokens/{chain}/{address}
- GET /api/search?q=...
- GET /api/watchlist
- POST /api/watchlist
- DELETE /api/watchlist/{chain}/{address}
- POST /api/alerts/test (Header: X-Admin-Token)
- POST /api/alerts/scan (Header: X-Admin-Token)
- POST /telegram/webhook (فقط برای Telegram)

## وضعیت تحویل
این commit کد Webhook تلگرام، دستورات، اسکن خودکار، ذخیره‌سازی قابل تنظیم برای دیسک Render، Blueprint و راهنمای تست/دیپلوی را آماده می‌کند. انتشار واقعی روی Render و اتصال به BotFather همچنان نیازمند ورود مالک حساب و واردکردن Secretها است. این نرم‌افزار ابزار غربالگری است، نه تضمین لیست‌شدن یا سود؛ میم‌کوین‌ها ریسک از دست رفتن کامل سرمایه دارند.
