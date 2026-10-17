'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const sdkRequire = require('node:module').createRequire(require.resolve('@solana/buffer-layout-utils'));
const adapter = sdkRequire('bigint-buffer');
assert.equal(sdkRequire('bigint-buffer/package.json').name, '@dbc-monitor/bigint-buffer-safe');
const fs = require('node:fs');
const path = require('node:path');
assert.deepEqual(fs.readFileSync(sdkRequire.resolve('bigint-buffer')),
  fs.readFileSync(path.join(__dirname,'../vendor/bigint-buffer-safe/index.cjs')));
assert.deepEqual(sdkRequire('bigint-buffer/package.json').dependencies||{},{});
assert.deepEqual(sdkRequire('bigint-buffer/package.json').scripts||{},{});
assert.deepEqual(Object.keys(adapter).sort(), ['toBigIntBE','toBigIntLE','toBufferBE','toBufferLE']);
let cases = 0;
for (const width of [0,1,2,4,8,16,32,64,128,1024]) {
  for (let i=0; i<20; i++) {
    const bytes = crypto.randomBytes(width);
    const hex = bytes.toString('hex');
    const expected = hex ? BigInt('0x'+hex) : 0n;
    assert.equal(adapter.toBigIntBE(bytes), expected);
    assert.deepEqual(adapter.toBufferBE(expected,width),bytes);
    assert.equal(adapter.toBigIntLE(Buffer.from(bytes).reverse()),expected);
    assert.deepEqual(adapter.toBufferLE(expected,width),Buffer.from(bytes).reverse());
    cases++;
  }
}
for (const value of [-1n,256n]) assert.throws(()=>adapter.toBufferLE(value,1),RangeError);
for (const width of [-1,1.1,Infinity,1025,NaN]) assert.throws(()=>adapter.toBufferBE(0n,width),RangeError);
assert.throws(()=>adapter.toBufferLE(1n,0),RangeError);
assert.throws(()=>adapter.toBufferBE(1,8),TypeError);
assert.throws(()=>adapter.toBigIntLE(new Uint8Array(8)),TypeError);
assert.throws(()=>adapter.toBigIntLE(Buffer.alloc(1025)),RangeError);
const layout = require('@solana/buffer-layout-utils');
for (const bits of [64,128,192,256]) {
  const field = layout['u'+bits]();
  for (const value of [0n,1n,(1n<<BigInt(bits))-1n]) {
    const bytes=Buffer.alloc(bits/8);
    field.encode(value,bytes,0);assert.equal(field.decode(bytes,0),value);cases++;
  }
}
console.log(JSON.stringify({adapter:'pure-js',cases,negative_controls:11,native_code:false}));
