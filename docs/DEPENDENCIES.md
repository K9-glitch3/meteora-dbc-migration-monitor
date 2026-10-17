# SDK dependency status / v0.4

The browser loads no Node SDK. The Python collector has no wallet or signing
path. A separate readiness sampler invokes the official DBC decoder locally on
bounded, read-only RPC responses. SDK quote comparisons remain offline checks.

- @meteora-ag/cp-amm-sdk 1.5.1: official DAMM v2 quote reference, MIT.
- @meteora-ag/dynamic-bonding-curve-sdk 2.0.0: official DBC decoder, MIT.
- Exact versions and integrity hashes: package-lock.json.
- SDK IDL/math attribution: METEORA_SDK_LICENSE.txt and upstream notices.

## Native dependency removed

The v0.3 tree retained bigint-buffer 1.1.5, affected by
[GHSA-3gc7-fjrx-p6mg](https://github.com/advisories/GHSA-3gc7-fjrx-p6mg).
Its upstream advisory has no fixed version. Disabling native builds was only
a mitigation, not a fix.

Version 0.4 replaces that package through an npm override with the local,
independently implemented @dbc-monitor/bigint-buffer-safe 1.0.0 adapter.
This is not a renamed copy of the vulnerable implementation. It has no native
code, bindings dependency, lifecycle script or external dependency.
Its four unsigned conversion functions reject negative values, overflow,
non-BigInt input and widths over 1,024 bytes. Unsupported inputs fail closed.
It is a deliberately narrower API, tested for this SDK use, not a universal
drop-in replacement.

Run npm ci --ignore-scripts, node scripts/check_bigint.cjs, npm audit,
and python scripts/check_pilot.py. On 17 October 2026, clean installation and
npm audit report zero known advisories. There are 212 valid conversion/layout
cases plus negative controls. All 120 previously published quote cases and
readiness decoder checks still pass, with unchanged case outputs. The quote
reports carry the new lockfile provenance and the adapter source hash.

This removes the identified dependency path; it does not establish that the
SDKs, adapter or monitor are vulnerability-free or independently audited.

## Licensing remains separate

dependency-inventory.json records current package declarations and notice hashes,
not legal clearance. rpc-websockets declares LGPL-3.0-only; chain has no package
license declaration or top-level notice; text-encoding-utf-8 has a LICENSE.md
without a package declaration. These remain redistribution review items.
Node modules are not bundled into the Python wheel or browser site.
