# SourceFarm

منصة تحكم كاملة للبوتات داخل Telegram — أنشئ وأدِر وطوِّر بوتاتك بسهولة.

## Run & Operate

- `cd artifacts/telegram-bot && python main.py` — تشغيل بوت Telegram
- Required env: `TELEGRAM_BOT_TOKEN` — توكن البوت من @BotFather
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- Python 3.12
- aiogram 3 — Telegram Bot framework
- FastAPI + uvicorn — web layer (health checks)
- PostgreSQL + SQLAlchemy (async) — database
- python-dotenv — environment config

## Where things live

- `artifacts/telegram-bot/main.py` — Entry point, bot startup
- `artifacts/telegram-bot/config.py` — Environment config
- `artifacts/telegram-bot/handlers/` — aiogram routers (start, source_tree, mode, menu)
- `artifacts/telegram-bot/keyboards/` — Inline keyboard builders
- `artifacts/telegram-bot/data/fake_sources.py` — Fake source data
- `artifacts/telegram-bot/database/` — SQLAlchemy models + session (User, Bot, Plan)

## Architecture decisions

- Polling mode (not webhook) for simplicity in dev
- All handlers in separate router modules for clean separation
- SQLAlchemy async engine with asyncpg driver
- DB tables auto-created on startup via `init_db()`
- Fake data in `data/` layer for UI prototype phase

## Product

- /start → رسالة ترحيب + 3 أزرار رئيسية
- 🌲 Source Tree → قائمة مصادر قابلة للتصفح مع Install/Details
- ⚡ Mode → Studio Mode (بدون كود) أو RealDev Mode (للمطورين)
- ☰ Menu → Profile, Plan, Wallet, Referral, Codes, Help, Settings

## User preferences

- الواجهة بالكامل داخل Telegram — لا موقع ويب ولا frontend
- رسائل وأزرار inline keyboard فقط
- الردود بالعربية
- العملة الداخلية اسمها **بذرة** (جمع: بذور) — وليس "نقطة"
- سعر الصرف: 1$ = 100 بذرة

## Gotchas

- تأكد من وجود DATABASE_URL و TELEGRAM_BOT_TOKEN قبل التشغيل
- Python path: نفّذ `main.py` دائماً من داخل `artifacts/telegram-bot/`
