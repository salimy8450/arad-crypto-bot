# ARAD MEME HUNTER PRO

A read-only, paper-mode meme-token discovery dashboard for Solana, Base, BNB Chain and Ethereum.

## Initial filters
- Market cap / FDV: <= USD 500,000 (FDV is a proxy when market cap is unavailable and is labelled)
- Pool liquidity: >= USD 50,000
- Strong alerts only
- No automated orders or wallet access

## Stack
- FastAPI + Python scanner
- DexScreener public API for initial market discovery
- PostgreSQL/Supabase schema in `db/schema.sql`
- Telegram Bot API notifications (optional)
- Responsive dashboard in `dashboard/index.html`

## Run locally
1. Copy `.env.example` to `.env` and fill optional Telegram/Supabase settings.
2. Install: `pip install -r requirements.txt`
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Open `http://localhost:8000` and API docs at `/docs`.

The scanner uses public market snapshots. Holder counts, holder growth, locked-liquidity proofs, social growth and official Ourbit listing evidence are not fabricated; they remain unknown until verified integrations are configured. A score is a ranking, not a statistical probability.

Paper mode produces research candidates only. It does not connect to wallets, sign transactions or place orders.
