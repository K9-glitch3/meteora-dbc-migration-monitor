# Developer pilot

I am testing whether migration evidence reduces the time developers spend resolving
ambiguous DBC-to-DAMM v2 events. I am continuing this work independently of the
Colosseum result. This is post-submission development, not a claim about work
completed during the judged period.

## A 15-minute first integration

1. Open [the watchlist](https://k9-glitch3.github.io/meteora-dbc-migration-monitor/monitor.html).
2. Add a pool, virtual pool or mint from the recorded sample. Watchlists stay in
   your browser. No wallet connection is required.
3. Inspect a migration and its transaction/raw-capture links. Compare the stage
   and missing evidence with your usual logs.
4. Fetch the versioned read API:
   `https://k9-glitch3.github.io/meteora-dbc-migration-monitor/api/v1/feed.json`.
5. Run `python examples/read_feed.py --address YOUR_PUBLIC_ADDRESS` from a clone.
   This reads a recorded snapshot. It is not a continuously hosted live stream.
6. Replay the source run with `python -m dbc_monitor verify evidence/RUN_NAME`.
   `source_run` in the feed supplies RUN_NAME.

## What each stage means

- BELOW_THRESHOLD: captured quote reserve is below 90% of the configured threshold.
- APPROACHING: at least 90%, but still below threshold. This does not predict timing.
- THRESHOLD_REACHED: reserve threshold reached; not proof all migration prerequisites hold.
- MIGRATED_FLAG: the account flag is set; not independent transaction verification.
- DETECTED: a notification was seen, without a verified finalized identity yet.
- FINALIZED_VERIFIED: finalized transaction identity and supported account roles match.
- UNRESOLVED / REJECTED: evidence is unavailable or fails validation, respectively.

The readiness sampler reads up to four recent finalized DBC transactions, then up
to eight pool/config pairs in the same getMultipleAccounts response. It is a sample,
not discovery of every active pool. Readiness and migration samples have separate
timestamps and may refer to different pools. Never infer a missing history stage.

## Alerts and API limitations

Browser activity records watched matches and newly observed stages when the page
refreshes a published snapshot. Old observations say "Recorded match". Clearing
activity does not establish a new on-chain state. There is no email, push or webhook
delivery and no background monitoring after closing the page. No uptime SLA applies.
The public feed is manually refreshed from bounded runs; refreshing the browser
does not trigger RPC collection. Staleness is explicit after five minutes.

Fields are versioned under api_version 1.0. Integers too large for JavaScript are
decimal strings. Treat unknown stages or schemas as unsupported, not successful.
The quotes.json endpoint is a separate same-state offline comparison report, not
an executable quote service. Never route trades from this pilot API.

## Feedback and repeat-use criteria

Use the repository's Developer pilot feedback issue template. Please supply:
the source run, public pool or transaction, expected and actual result, elapsed
integration time, a confusing case, and whether you returned on a second date.
Do not include keys, private endpoints, wallet secrets or customer information.

I will count a pilot only after an external developer explicitly agrees. An
integration means their system actually consumes the feed and they confirm it.
Repeat use requires a second dated use, not two requests from my own test client.
The initial target is three accepted pilots and one confirmed integration.

## Feedback-driven release gate

I will record external feedback before changing the contract, add a failing fixture
for reproducible defects, ship a tested correction, and ask the reporter to verify
it. A rejected hypothesis or declined pilot is useful evidence, not traction.
