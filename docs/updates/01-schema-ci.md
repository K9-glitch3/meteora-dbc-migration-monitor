# Versioned observations and automated verification

I have added a versioned observation schema to DBC Migration Monitor. Every record now carries its source, slot, commitment, freshness, result, reason and comparison scope. This makes missing and unsupported evidence explicit instead of turning it into a success.

I have also added automated tests and Windows/Linux CI on Python 3.10 and 3.12. The release suite now contains 44 tests, including malformed inputs, stale evidence, slot conflicts, cancellation and checksum tampering.

The supported comparison in this release is migration identity. It is not a claim that swap quotes or trading outcomes have been verified.

https://github.com/K9-glitch3/meteora-dbc-migration-monitor/actions/workflows/ci.yml
https://k9-glitch3.github.io/meteora-dbc-migration-monitor/observation.schema.json
