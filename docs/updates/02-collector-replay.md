# Read-only collection and reproducible replay

I have added a bounded, read-only Solana collector. It discovers DBC migration candidates, retrieves finalized transactions, checks supported instruction roles, and records DAMM v2 pool snapshots and account updates.

The collector preserves duplicates, conflicts, missing evidence and connection gaps as distinct outcomes. Reconnection is implemented and tested, but there is no claim of complete network coverage or historical gap backfill.

Each completed run can be frozen into a checksummed capture, observation file and manifest. Anyone can run the same offline replay and verify the published classifications. The package contains no wallet, signing or transaction-submission path.

https://github.com/K9-glitch3/meteora-dbc-migration-monitor#collect-a-bounded-sample
https://github.com/K9-glitch3/meteora-dbc-migration-monitor/blob/master/docs/ARCHITECTURE.md
