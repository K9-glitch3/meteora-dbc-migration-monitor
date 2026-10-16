# Supported protocol scope

## v0.3 additions (16 October 2026, post-submission)

The separate quote report checks exact-input A-to-B and B-to-A amounts 1, 1,000,
1,000,000 and 1,000,000,000 atomic units. It compares output, next sqrt price and
total fee against @meteora-ag/cp-amm-sdk 1.5.1 using identical captured bytes and
the same current-point parameter. Static fees only; standard initialized SPL
mints; concentrated liquidity; collection modes 0/1; no referral. Timestamp-mode
current point uses capture wallclock, not the snapshot slot's block time; this is
an offline arithmetic comparison, not proof the quote was executable then.
Dynamic fees, Token-2022, compounding, non-static schedules and out-of-range quotes
are explicitly excluded. No swap is submitted and no slippage/fill is claimed.

Readiness uses the official DBC SDK 2.0.0 decoder on captured account bytes.
Pool/config pairs share one finalized RPC context. Threshold progress and migrated
flags remain separate from finalized transaction identity. The public API is a
recorded sample with timestamps, not a continuously hosted feed.

Reconnect backfill scans at most 100 signatures and retrieves at most five
transactions, overlapping the last seen slot by 64. Budget exhaustion, unresolved
transactions and failure to reach the boundary prevent a complete-history result.
Even complete=true refers only to that finalized history query and its stated
boundary, not full network coverage, confirmed forks or the reconnect interval.
Account-update history is not backfilled. The reconnect/backfill path has
fault-injection tests; an uninterrupted mainnet capture does not exercise recovery.

The v0.2 observation verdict contract below is preserved unchanged.

## Pinned source
Meteora dynamic-bonding-curve-sdk commit:
[a8e5fedf1cc62e488da477a19ae3c6ad9a707f80](https://github.com/MeteoraAg/dynamic-bonding-curve-sdk/tree/a8e5fedf1cc62e488da477a19ae3c6ad9a707f80)

IDLS under `packages/dynamic-bonding-curve/src/idl/`:
- `dynamic-bonding-curve/idl.json`
- `damm-v2/idl.json`

MIT attribution: `METEORA_SDK_LICENSE.txt`. Machine-readable offsets and source
metadata are in `dbc_monitor/pool_layout.json`.

## Migration identity
DBC: `dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN`.
DAMM v2: `cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG`.

Only the pinned `migration_damm_v2` discriminator and exact argument length are
supported. Program, authority and account roles are checked. Top-level and inner
instructions and loaded addresses are supported. Not every PDA is rederived.

## Pool state
1112 bytes with the pinned pool discriminator, correct owner and non-executable
status. Layout versions 0/1 and collect-fee-mode values 0/1/2 are accepted
**for state decoding only**.

`token_b_atomic / token_a_atomic = sqrt_price_q64 ** 2 / 2 ** 128`

Numerator, denominator, sqrt price and liquidity are decimal strings to preserve
integer precision. Mint decimals are not silently applied. Status and fee mode
are reported, not treated as proof that swaps will execute.

Dynamic fees, transfer fees, Token-2022 extensions, slippage, partial fills and
independent historical swap-quote reconstruction are not validated in v0.2.
Pool-state decoding never produces a quote-match verdict.
