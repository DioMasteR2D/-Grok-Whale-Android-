# Grok Bot operating standards — approved reference prompt

This document records the exact operating criteria shown in the user's Grok Bot reference image. These are integration-layer strategy gates; they do not replace or modify any upstream project's own defaults, thresholds, algorithms, or configuration files.

## Session

- Timezone: Europe/Athens
- Active session: 13:30–21:30 local time

## Wallet discovery and ranking

- Discover Solana whale wallets through SolScope (GMGN leaderboards) and SoulWinners.
- Rank wallets by SoulWinners BES and retain the top 10.
- Qualification window: 30 days.
- Minimum win rate: 60%.
- Minimum trades: 15.
- Minimum ROI: 50%.
- Archetypes: Core Alpha, Moonshot, Sniper.
- Exclude CEX, market makers, bridges, and developers.

## Mandatory Atlas entry gates

A meme-token entry is eligible only when every condition is evidenced:

1. Origin wallet is in the qualified top 10.
2. Atlas PropagationScore is at least 0.70.
3. At least 2 whale wallets follow within 5 minutes (300 seconds).
4. Crowding is strictly below 0.55.
5. LP is burned.
6. Mint authority is revoked.

Missing evidence fails closed. LP burn and mint revocation are separate checks.

## Position and exit rules

- Maximum position size: 8% of portfolio value.
- Stop loss: -6%.
- Exit when the origin whale exits.

## Phantom and execution safety

- Intended wallet provider: Phantom.
- Each future live transaction requires explicit Phantom approval.
- Current application mode remains paper only; live trading is disabled.
- The current API strategy endpoint only evaluates gates; it does not create orders, sign transactions, or execute trades.

## Source preservation

SolScope, SoulWinners, and Atlas upstream repositories remain unchanged. These criteria are applied by the integration project around their outputs. No upstream defaults are overwritten.
