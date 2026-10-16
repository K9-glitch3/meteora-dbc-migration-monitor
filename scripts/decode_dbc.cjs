// Offline decoding only; no provider, wallet or transaction builder is instantiated.
const fs = require('node:fs');
const {BorshAccountsCoder} = require('@coral-xyz/anchor');
const {DynamicBondingCurveIdl} = require('@meteora-ag/dynamic-bonding-curve-sdk');
const coder = new BorshAccountsCoder(DynamicBondingCurveIdl);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
if (!Array.isArray(input) || input.length > 100) throw new Error('Bounded array required');
const result = input.map(item => {
  const account = item.account;
  if (!account || account.owner !== 'dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN' || account.executable !== false) return null;
  try {
    const bytes = Buffer.from(account.data[0], 'base64');
    if (account.data[1] !== 'base64' || bytes.length > 8192) return null;
    if (bytes.length !== coder.size(item.kind === 'config' ? 'PoolConfig' : 'VirtualPool')) return null;
    if (item.kind === 'config') {
      const c = coder.decode('PoolConfig', bytes);
      return {address:item.address, threshold:c.migration_quote_threshold.toString(), migration_option:c.migration_option, quote_mint:c.quote_mint.toBase58()};
    }
    const p = coder.decode('VirtualPool', bytes).pool_state;
    return {address:item.address, config:p.config.toBase58(), base_mint:p.base_mint.toBase58(),
      quote_reserve:p.quote_reserve.toString(), migrated:p.is_migrated, migration_progress:p.migration_progress};
  } catch { return null; }
});
process.stdout.write(JSON.stringify(result));
