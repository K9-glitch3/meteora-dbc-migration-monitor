# Thirty-minute mainnet run: results and limitations

I completed a 30-minute read-only mainnet run on 16 October 2026, from 02:48 to 03:18 UTC. It observed 34 migration candidates: 31 matched finalized migration identities, two transactions failed, and one finalized transaction remained unavailable.

The capture also contains 325 pool-state observations across 31 distinct pools, including confirmed updates from up to four watched pools. Ten RPC errors are retained. There were no reconnects or queue overflows in this run, so those paths are covered by tests rather than claimed as demonstrated by this capture.

The public corpus contains 411 capture records and 403 derived observations with checksums and reproducible replay. This is evidence of the monitor's current behaviour, not an accuracy benchmark, independent audit or swap-price verification. My next validation target is independent same-state quote comparison and external developer pilots.

https://github.com/K9-glitch3/meteora-dbc-migration-monitor/blob/master/docs/RUN_2026-10-16.md
https://github.com/K9-glitch3/meteora-dbc-migration-monitor/tree/master/evidence/mainnet-2026-10-16
