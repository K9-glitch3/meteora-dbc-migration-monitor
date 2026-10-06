# Architecture and scope

## Private prototype boundary

The internal system contains four relevant layers:

1. Migration discovery and admission checks.
2. Pool-role and keeper-ticket binding.
3. Account-state streaming and freshness handling.
4. Supported DAMM v2 integer quote arithmetic and semantic evidence.

Execution, wallets, signing, strategy, and operational controls are deliberately
excluded from this public reviewer package.

## Reviewer package

`dbc_monitor.evidence` validates the two accounting identities in the retained
aggregate evidence. It does not contact an RPC endpoint and cannot verify the
truth of the original observations.

`dbc_monitor.boundary` demonstrates the intended result semantics:

- missing transactions and non-swap writes produce `NO_CONCLUSION`;
- unsupported pool configurations remain explicit;
- stream or math mismatches are rejected;
- only complete, supported matching observations receive
  `SUPPORTED_COMPARISON`.

The browser dashboard presents the same counts without converting exclusions
into a headline accuracy percentage.

## Planned release path

1. Resolve attribution and redistribution permissions for any derived source.
2. Add transaction-level public fixtures with sensitive fields removed.
3. Publish supported layout and fee-mode documentation.
4. Add a read-only live integration example with reorganisation and freshness
   behaviour.
5. Seek independent developer pilots and document feedback.
