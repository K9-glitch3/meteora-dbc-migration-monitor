// Offline oracle: the official pinned SDK consumes exactly the captured pool bytes.
const fs = require('node:fs');
const sdk = require('@meteora-ag/cp-amm-sdk');
const {BN} = require('@coral-xyz/anchor');
function camel(value) {
  if (Array.isArray(value)) return value.map(camel);
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    return Object.fromEntries(Object.entries(value).map(([k,v]) => [k.replace(/_([a-z])/g, (_,c)=>c.toUpperCase()), camel(v)]));
  }
  return value;
}
const requests = JSON.parse(fs.readFileSync(0, 'utf8'));
if (!Array.isArray(requests) || requests.length > 10000) throw new Error('Bounded array required');
const result = requests.map(r => {
  try {
    const pool = camel(sdk.cpAmmCoder.accounts.decode('Pool', Buffer.from(r.account, 'base64')));
    const direction = r.direction === 'AtoB' ? sdk.TradeDirection.AtoB : sdk.TradeDirection.BtoA;
    const answer = sdk.getSwapResultFromExactInput(pool, new BN(r.amount), sdk.getFeeMode(pool.collectFeeMode, direction, false), direction, new BN(r.point));
    return {output_amount: answer.outputAmount.toString(), next_sqrt_price: answer.nextSqrtPrice.toString(),
      total_fee: answer.claimingFee.add(answer.protocolFee).add(answer.compoundingFee).add(answer.referralFee).toString()};
  } catch (error) { return {error: error.constructor.name}; }
});
process.stdout.write(JSON.stringify(result));
