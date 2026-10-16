# Reference SDK dependencies

The browser dashboard and Python collector do not load the Node SDK dependency tree.
Node tooling is an offline development/reference check, not a server or trading path.

- @meteora-ag/cp-amm-sdk 1.5.1: official DAMM v2 quote reference, MIT.
- @meteora-ag/dynamic-bonding-curve-sdk 2.0.0: official DBC account decoder, MIT.
- Exact versions/integrity hashes: package-lock.json.
- SDK IDL/math attribution: docs/METEORA_SDK_LICENSE.txt and upstream package licenses.

Install with `npm ci --ignore-scripts`. Do not run npm rebuild on this reference
environment. The bigint-buffer native addon must remain absent; the package uses
its pure-JavaScript fallback. Captured accounts are bounded and locally supplied.

On 16 October 2026, npm audit initially reported dependency advisories involving
toml, jayson/stream-json/uuid and bigint-buffer. Overrides pin toml 4.2.0 and jayson
5.0.0; the SDK comparison is rerun against that exact lockfile.

Residual: bigint-buffer 1.1.5 has GHSA-3gc7-fjrx-p6mg, a native toBigIntLE buffer
overflow advisory with no upstream fixed version in this tree. Five high-severity
package nodes remain flagged through that dependency chain. Disabling install
scripts and verifying no native addon is built reduces exposure to that native
path; it does not mean the dependency is patched or the project is audited.
Do not deploy these reference dependencies as a public service. Reassess before
accepting arbitrary untrusted inputs or enabling native builds.

Primary advisory: https://github.com/advisories/GHSA-3gc7-fjrx-p6mg
SDK sources: https://github.com/MeteoraAg/damm-v2-sdk and
https://github.com/MeteoraAg/dynamic-bonding-curve-sdk.
