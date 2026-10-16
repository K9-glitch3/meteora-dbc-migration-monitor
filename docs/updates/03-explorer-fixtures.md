# Public evidence explorer and transaction-level fixtures

I have published an interactive evidence explorer with search, result/stage/freshness filters, pagination, per-record details, transaction links and filtered JSON downloads. The page displays recorded evidence rather than pretending to be a live feed.

The public repository now includes raw mainnet responses and deterministic observations, with a separate, clearly labelled synthetic fixture for failure cases such as invalid owners, unsupported layouts and stale slots.

Pool prices are exposed as exact atomic-unit ratios, preserving integer precision. They are not labelled as independently verified swap quotes. The explorer has been checked on desktop and mobile layouts.

https://k9-glitch3.github.io/meteora-dbc-migration-monitor/
https://github.com/K9-glitch3/meteora-dbc-migration-monitor/tree/master/evidence
