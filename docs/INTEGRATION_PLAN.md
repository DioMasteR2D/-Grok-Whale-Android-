# Integration plan

## Source responsibilities

| Upstream | Intended responsibility | Integration status |
|---|---|---|
| Frisbiz/solscope | GMGN smart-money leaderboard discovery and wallet performance fields | Not connected |
| forgottenpeak/soulwinners | Helius wallet activity, persistent wallet history and trader archetypes | Not connected |
| AtlasOnchain/Atlas | Origin/follower sequencing, sector overlap, propagation and crowding | Not connected |

## Required next steps

1. Inspect each upstream tree, dependency files, license and runtime requirements.
2. Implement isolated adapters with normalized schemas; do not merge incompatible runtimes blindly.
3. Add source timestamps, provenance, rate-limit handling, retries and stale-data indicators.
4. Build a reproducible backend test suite with fixture data.
5. Connect the Android client to the backend and add loading/error/empty states.
6. Add a deterministic paper ledger and risk controls before any wallet integration.

## Important compatibility note

Atlas documents TypeScript/Bun and the Claude Agent SDK. This project will initially treat its flow logic as a separately deployable adapter/service. "Grok" is only the product name at this stage; an analysis provider is not configured.


## Read-only data integration (implemented scaffold)

The FastAPI backend now exposes:
- `GET /api/v1/whales?period=7d&limit=100`: SolScope GMGN PnL/win-rate leaderboard responses plus SoulWinners qualified-wallet rows.
- `GET /api/v1/atlas/flows?limit=10`: recent Helius parsed transactions for configured public wallet addresses.
- `GET /api/v1/paper-portfolio`: paper-only empty ledger; no execution path.

Backend environment:
- `GMGN_PROXY_URL`: base URL of the existing SolScope proxy service.
- `SOULWINNERS_DB_PATH`: path to SoulWinners' existing SQLite database on the backend host. It is opened with SQLite read-only mode.
- `HELIUS_API_KEY`: Helius API key stored as a server secret, never committed to Git.
- `ATLAS_SEED_WALLETS`: comma-separated public Solana wallet addresses to inspect.

Limitations still to complete:
- SoulWinners must be deployed with its database accessible to this backend (or a read-only API export must be added).
- The Atlas endpoint currently returns raw Helius activity. Atlas' own Anthropic-powered agent and propagation/crowding scores still require deploying the Atlas service and exposing a read-only endpoint.
- SolScope/GMGN response shape and upstream availability must be validated against live responses.
- No real trading, wallet signing, or Phantom authorization is implemented.
