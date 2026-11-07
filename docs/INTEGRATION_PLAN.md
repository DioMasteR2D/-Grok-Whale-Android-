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
