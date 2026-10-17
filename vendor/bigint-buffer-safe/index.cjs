'use strict';
// Independently implemented adapter for the four functions used by SPL Token.
// Reject truncation and unbounded allocation rather than emulate native behavior.
const MAX_BYTES = 1024;
function input(bytes) {
  if (!Buffer.isBuffer(bytes)) throw new TypeError('Expected Buffer');
  if (bytes.length > MAX_BYTES) throw new RangeError('Buffer exceeds 1024 bytes');
}
function toBigIntBE(bytes) {
  input(bytes);
  let result = 0n;
  for (const byte of bytes) result = (result << 8n) | BigInt(byte);
  return result;
}
function toBigIntLE(bytes) {
  input(bytes);
  let result = 0n;
  for (let i = bytes.length - 1; i >= 0; i--) result = (result << 8n) | BigInt(bytes[i]);
  return result;
}
function encode(value, width, little) {
  if (typeof value !== 'bigint') throw new TypeError('Expected bigint');
  if (!Number.isSafeInteger(width) || width < 0 || width > MAX_BYTES) throw new RangeError('Invalid width');
  if (value < 0n || value >= (1n << BigInt(width * 8))) throw new RangeError('Unsigned value does not fit');
  const result = Buffer.alloc(width);
  for (let i = 0; i < width; i++) {
    result[little ? i : width - i - 1] = Number(value & 255n);
    value >>= 8n;
  }
  return result;
}
module.exports = {toBigIntLE, toBigIntBE,
  toBufferLE: (value, width) => encode(value, width, true),
  toBufferBE: (value, width) => encode(value, width, false)};
