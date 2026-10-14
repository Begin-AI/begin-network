// Independent Node.js built-in crypto interoperability harness, not a host verifier.
// Python remains responsible for full envelope/policy/replay validation.
import { createPublicKey, generateKeyPairSync, sign, verify, createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const b64 = (value) => Buffer.from(value).toString('base64url');
const raw = (value) => {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value)) throw Error('invalid base64url');
  const result = Buffer.from(value, 'base64url');
  if (b64(result) !== value) throw Error('noncanonical base64url');
  return result;
};
const kid = (publicBytes) => 'ed25519:' + b64(createHash('sha256').update(publicBytes).digest());

function verifyToken(token, publicBytes) {
  if (typeof token !== 'string') throw Error('token type');
  const parts = token.split('.');
  if (parts.length !== 3) throw Error('compact JWS required');
  const header = JSON.parse(raw(parts[0]).toString('utf8'));
  if (Object.keys(header).sort().join(',') !== 'alg,kid,typ' || header.alg !== 'EdDSA' || header.typ !== 'begin+jws-v1' || header.kid !== kid(publicBytes)) throw Error('header mismatch');
  if (publicBytes.length !== 32) throw Error('public key length');
  const publicKey = createPublicKey({key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), publicBytes]), format: 'der', type: 'spki'});
  if (!verify(null, Buffer.from(parts[0] + '.' + parts[1], 'ascii'), publicKey, raw(parts[2]))) throw Error('invalid signature');
  return JSON.parse(raw(parts[1]).toString('utf8'));
}

try {
  const input = JSON.parse(readFileSync(0, 'utf8'));
  if (input.action === 'verify') {
    console.log(JSON.stringify({valid: true, payload: verifyToken(input.token, raw(input.public))}));
  } else if (input.action === 'sign') {
    const keys = generateKeyPairSync('ed25519');
    const spki = keys.publicKey.export({format: 'der', type: 'spki'});
    const publicBytes = spki.subarray(-32);
    const identity = kid(publicBytes);
    const payload = {...input.payload, sender: identity};
    const header = {alg: 'EdDSA', typ: 'begin+jws-v1', kid: identity};
    const content = b64(JSON.stringify(header)) + '.' + b64(JSON.stringify(payload));
    console.log(JSON.stringify({public: b64(publicBytes), kid: identity, payload, token: content + '.' + b64(sign(null, Buffer.from(content, 'ascii'), keys.privateKey))}));
  } else throw Error('unknown action');
} catch (error) {
  console.log(JSON.stringify({valid: false, error: error.message}));
  process.exitCode = 1;
}
