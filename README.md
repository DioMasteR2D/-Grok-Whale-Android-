# DioMasteR2D — Grok Whale Android

Android-first Solana whale-intelligence and paper-trading project. The app combines independently sourced wallet discovery, Helius observations, Grok analysis through xAI, conservative on-chain checks, and a persistent paper ledger.

## Current implementation

- Native Android client: Kotlin + Jetpack Compose.
- API: Python + FastAPI.
- Wallet discovery: existing SolScope/GMGN proxy adapter, with a public dEdge discovery fallback for Helius observations.
- Wallet performance: read-only SoulWinners database adapter. It only ranks rows with measured 30-day fields and a computed BES; it does not manufacture missing history.
- Activity: bounded Helius requests with low concurrency, retries, and a short response cache.
- AI: Grok via xAI Chat Completions. Model output is advisory and explicitly marked unverified.
- Token checks: Solana finalized RPC checks mint authority and, only when the correct pool LP mint is supplied, checks whether its total supply is zero.
- Prices: Jupiter Price API v3. Missing prices remain missing.
- Portfolio: persistent PostgreSQL paper ledger; maximum 10 open positions by default and maximum 8% of current paper equity per position.
- Wallet: Android Mobile Wallet Adapter connection flow. No seed phrase/private key handling and no transaction signing or sending.

## Important integration boundaries

This is an integration project, not a vendored copy of the upstream projects.

| Upstream | Intended use | Current boundary |
|---|---|---|
| [SolScope](https://github.com/Frisbiz/solscope) | GMGN smart-wallet leaderboard | Adapter calls an existing proxy. Upstream repository currently has no declared license; its source is not copied. |
| [SoulWinners](https://github.com/forgottenpeak/soulwinners) | Wallet monitoring, history and classification | Upstream declares MIT. This project reads an existing database; it does not yet run the upstream 30-day collector. |
| [Atlas](https://github.com/AtlasOnchain/Atlas) | Origin/follower propagation, sector context and crowding | Upstream repository currently has no declared license. Current adapter is Helius observation + Grok analysis, not the full Atlas runtime. |

The SoulWinners table/schema initialization is **not ingestion**. To qualify wallets correctly, deploy the upstream collector and populate the same PostgreSQL database (or provide a verified export/API). Until measured 30-day win rate, trades, ROI, archetype and BES are present, candidates are excluded.

Grok's propagation/crowding estimates are not verified on-chain facts and cannot independently pass entry gates. The Atlas propagation score, follower timing and crowding calculation still require a verified implementation or deployed Atlas read-only service. LP mint discovery is also not implemented; the caller must supply the actual pool LP mint, and the endpoint warns that it cannot establish pool association itself.

## Strategy and safety

- Timezone: Europe/Athens; session: 13:30–21:30.
- Wallet ranking: top 10 by BES, 30-day evidence, win rate at least 60%, at least 15 trades, ROI at least 50%, approved archetypes only; exclude CEX, market makers, bridges and developer wallets.
- Entry gates: origin in qualified top 10; propagation at least 0.70; at least two following whales within 300 seconds; crowding strictly below 0.55; LP burned; mint authority revoked.
- Position cap: 8% of paper equity; maximum 10 open paper positions by default.
- Stop loss: -6%; observed origin-wallet exit also closes the linked paper position.
- Missing evidence fails closed.
- Live trading is hard-disabled. Jupiter endpoint is quote/preview only; it does not return a transaction for signing or send a swap.

## Backend setup

Use Python 3.12+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Configure secrets on the backend host (never commit them):

- `GMGN_PROXY_URL`: base URL of the existing SolScope proxy.
- `SOULWINNERS_DATABASE_URL`: PostgreSQL URL used for the SoulWinners integration tables and paper ledger.
- `SOULWINNERS_DB_PATH`: optional path to an existing SoulWinners SQLite database, opened read-only.
- `HELIUS_API_KEY`: read-only wallet activity and Helius RPC.
- `XAI_API_KEY`: xAI API key for Grok analysis.
- `GROK_MODEL`: model identifier supported by the xAI account.
- `JUPITER_API_KEY`: optional key for Jupiter API access.
- `SOLANA_RPC_URL`: optional explicit Solana JSON-RPC URL.
- `MAX_OPEN_POSITIONS`: default 10.

The API health endpoint is `/health`; interactive API docs are `/docs`. Do not expose the backend publicly without TLS and suitable access controls.

## Android build

The GitHub Actions workflow builds a debug APK and publishes it as a workflow artifact. It also runs backend safety tests. Open the Actions run for the branch/PR and download the `DioMasteR2D-GrokBot-debug` artifact after the build succeeds.

## Tests

```bash
cd backend
PYTHONPATH=. python -m pytest -q
```

Tests cover fail-closed strategy gates, the strict crowding threshold and validation of untrusted Grok output.

## Not yet production-complete

1. Install and verify the real SoulWinners 30-day ingestion collector.
2. Deploy/implement Atlas-native propagation, 5-minute follower verification and crowding.
3. Discover and validate the actual LP mint for each pool.
4. Add persistent daily risk accounting, observability and deployment secrets.
5. Verify the Render deployment and Android APK on a physical device.
6. Keep all live transaction creation/signing disabled until every independent safety and wallet-approval check has been tested.
