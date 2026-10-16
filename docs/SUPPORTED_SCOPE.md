# Supported protocol scope

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
