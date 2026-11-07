# DioMasteR2D — Grok Whale Android

Android-first Solana whale-intelligence app combining adapters for the three selected upstream projects:

- [SolScope](https://github.com/Frisbiz/solscope) — GMGN wallet leaderboard discovery and wallet metrics.
- [SoulWinners](https://github.com/forgottenpeak/soulwinners) — Helius-backed wallet monitoring, SQLite history and trader classification.
- [Atlas](https://github.com/AtlasOnchain/Atlas) — origin/follower propagation, sector context and crowding analysis.

## Status

**Phase 0 — integration scaffold.** This repository is a new integration project, not a copy or claim of ownership of the upstream repositories. Their source code has not yet been vendored. Before importing any source, verify each upstream license and preserve its notices. SoulWinners advertises MIT; the SolScope license and Atlas license should be checked in their upstream repositories before copying code.

## Safety defaults

- Paper trading only. No transaction signing or live order submission.
- No seed phrases or private keys are collected or stored.
- Phantom connection is a future read-only wallet/session integration; any future transaction must require explicit wallet approval.
- Whale scores and alerts are research signals, not guarantees or financial advice.

## Planned architecture

```
Android app (Kotlin + Jetpack Compose)
       |
       | HTTPS / JSON
       v
Integration API (Python / FastAPI)
  | SolScope adapter  -> GMGN wallet leaderboard data
  | SoulWinners       -> Helius wallet activity + SQLite metrics
  | Atlas adapter     -> origin/follower + propagation/crowding
  | Signal fusion     -> explainable score + paper portfolio
       |
       v
SQLite (development) / PostgreSQL (deployment)
```

Atlas currently documents a Claude Agent SDK dependency, not Grok. The app will keep the analysis provider behind an interface; no claim is made that Grok is already wired in.

## Repository layout

- `android/` — native Android client.
- `backend/` — API and integration adapters.
- `docs/` — architecture, source mapping and verification notes.

## Development

The initial scaffold is being added in stages. Build instructions will be finalized after the Android Gradle wrapper and backend dependency lock are added.
