# Architecture and evidence boundaries

## Public v0.3 additions

Offline quote arithmetic in quotes.py is checked against a separately executed,
pinned official SDK. Node dependencies are development-only and never loaded by
the collector or browser. Separate reports preserve the original identity verdicts.

The readiness sampler discovers a bounded set of active accounts, then captures
pool/config pairs in one finalized RPC context. The SDK decoder only decodes
captured bytes. lifecycle.py classifies observations without predicting migrations.

build_feed.py derives the public recorded JSON API from frozen evidence. The
browser watchlist keeps addresses/activity locally, deduplicates stage alerts,
exposes stale timestamps and links back to evidence. No backend receives watchlists.

recovery.py adds budgeted finalized signature/transaction backfill after reconnect.
It distinguishes unfinished history from a reached boundary and retries seen but
unfinalized candidates. It does not recover arbitrary account-update history or
prove complete network coverage. See SUPPORTED_SCOPE.md and DEPENDENCIES.md.

## Historical public v0.2 pipeline
1. Confirmed DBC logs identify candidate migrations, not proven migrations.
2. A bounded worker retrieves finalized transactions, preserving raw responses.
3. Supported top-level and CPI instructions are decoded and their roles checked.
4. Pool snapshots use a minimum context slot equal to the migration slot.
   Up to the configured pool limit receive confirmed account subscriptions.
5. Schema-validated observations are deterministically derived and frozen.
6. The browser loads those same exported observations.

## Integrity is not independent authenticity
Hashes bind the saved capture and derived records. Replay verifies classification
from that capture. Neither independently proves the RPC provider's claims.
Finality is the requested provider commitment; signatures are checked for identity,
not cryptographically reverified.

Manifests record Git HEAD at freeze time and a replay-source hash. A dirty tree
can differ from HEAD. New collectors also record a source hash at launch.
The first 2026-10-16 development capture predates that field; it must not be
described as collected by the final release commit. Its raw bytes are unchanged.

## Failure and reorganisation handling
- Duplicate signatures are not repeatedly queued. Changed slots are conflicts.
- A finalized transaction at a different slot is rejected for identity matching.
- Confirmed account updates are provisional. Older slots are stale; identical
  pool/slot/payload observations are duplicates.
- Reconnection restores subscriptions and records gaps. There is no historical
  gap backfill, rollback state machine or guarantee of complete coverage.
- Missing finalized transactions remain unavailable after bounded retries.
- Transaction freshness is capture time minus block time, default 120 seconds
  with five seconds of clock skew. Account wall-clock freshness remains unknown.
- Unknown layouts/fee modes are unsupported. Missing evidence is not success.

## Limits
One worker, a 64-item queue, at most 16 watched pools (default four), 1-3600
seconds, default 20,000 journal records, bounded message sizes and a 90-second
drain. Finalization writes may slightly exceed the stream record threshold.
RPC calls time out after 12 seconds; process shutdown may await an in-flight
thread. No wallet, signing, execution, key storage or private strategy is included.

The old aggregate validator only checks accounting identities. Its historical
private swap-comparison summary is distinct from the new migration-identity
records. The next separate validation step is same-state, independent swap-quote
comparison followed by external developer pilots.
