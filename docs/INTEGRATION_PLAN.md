# Integration plan and verified boundaries

## Upstream responsibilities and licensing

| Project | Intended responsibility | License check | Integration |
|---|---|---|---|
| Frisbiz/solscope | GMGN leaderboard discovery and wallet metrics | No license declared in repository metadata at audit time; do not copy source without permission | Read-only HTTP adapter to an existing proxy |
| forgottenpeak/soulwinners | Helius monitoring, wallet history, trader archetypes | MIT declared by upstream repository | Read-only DB adapter; upstream collector still must be deployed |
| AtlasOnchain/Atlas | Origin/follower propagation, sector overlap and crowding | README claims MIT, but no LICENSE file is present in the repository tree; treat licensing as unverified pending owner confirmation | Independent Helius-derived approximation + Grok advisory analysis; not equivalent to full Atlas runtime |

Upstream source repositories remain unchanged. The integration repository does not vendor their source.

## Implemented in this repository

- FastAPI service with health/status, whale, flow, signals, on-chain checks, Jupiter price/quote preview, strategy evaluation and paper portfolio endpoints.
- SolScope proxy adapter and discovery fallback.
- SoulWinners PostgreSQL/SQLite read-only adapter. Schema initialization creates tables only; it does not ingest history.
- Helius activity adapter with bounded concurrency, retry handling and a short cache.
- xAI Grok analysis adapter. AI outputs are marked unverified and cannot substitute for chain evidence.
- Independent deterministic origin/follower analysis over qualified-wallet Helius SWAP observations, using a clearly labeled Atlas-compatible approximation; not the upstream Atlas implementation.
- Finalized RPC checks for mint authority and supplied LP mint supply.
- Jupiter Price v3 adapter with explicit missing-price handling.
- Persistent paper ledger with 8% position cap, ten-position cap by default, -6% stop and origin-wallet exit handling.
- Android Compose dashboard and wallet-connect flow without transaction signing.
- CI workflow for backend safety tests and debug APK build.

## Mandatory remaining work

1. Deploy the actual SoulWinners collector and verify a continuous 30-day history in the shared database. The upstream public configuration contains hard-coded credentials; do not copy or execute it as-is, and have the upstream owner rotate any exposed keys. Do not call schema creation ingestion.
2. Verify the exact upstream schema and source semantics for ROI, measured win rate, trade count, average buy size and BES.
3. Implement or deploy Atlas-native origin/follower matching, follower timestamps within 300 seconds, propagation score and crowding score. Grok estimates are advisory only.
4. Discover the actual LP mint from the pool/program and verify pool association before checking its total supply. Current API only checks a caller-supplied LP mint.
5. Add durable daily loss limits and auditable risk/exit events.
6. Configure xAI, Helius, PostgreSQL, SolScope proxy and optional Jupiter credentials as host secrets.
7. Verify deployed API URL, Render health, Android install and physical Phantom compatibility.
8. Only after all checks are independently tested, consider a separately reviewed wallet-approved transaction flow. Live trading remains disabled.

## CI

The GitHub Actions workflow runs Python safety tests and builds a debug APK for feature branch pushes and pull requests. The APK is downloadable from the successful workflow run artifact.
