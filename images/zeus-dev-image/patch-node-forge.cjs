// patch-node-forge.cjs: backport CVE-2026-85393's nested DigestAlgorithm check.
// Source: https://github.com/digitalbazaar/forge/pull/1152
// Keep upstream version metadata unchanged; scanners may still flag 1.4.0.
// Remove this carry after upgrading to an upstream release with the fix.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const root = process.env.FORGE_TEST_ROOT || '/opt/cline';
const packages = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'))).packages;
const targets = Object.keys(packages).filter(p => p.endsWith('node_modules/node-forge'));
assert(targets.length, 'node-forge dependency disappeared; review/remove backport');
for (const target of targets) {
  const dir = path.join(root, target);
  assert.equal(JSON.parse(fs.readFileSync(path.join(dir, 'package.json'))).version, '1.4.0');
  const file = path.join(dir, 'lib/rsa.js');
  const before = 'obj.value.length !== 2) {';
  const after = "obj.value.length !== 2 ||\n            obj.value[0].value.length !== (('parameters' in capture) ? 2 : 1)) {";
  const source = fs.readFileSync(file, 'utf8');
  if (process.argv.includes('--check')) {
    assert(source.includes(after), 'node-forge backport missing');
  } else {
    assert.equal(source.split(before).length - 1, 1, 'upstream RSA source changed');
    fs.writeFileSync(file, source.replace(before, after));
  }

  const forge = require(dir);
  // Public upstream regression fixture: nested AlgorithmIdentifier garbage must fail.
  const modulus = 'E932AC92252F585B3A80A4DD76A897C8B7652952FE788F6EC8DD640587A1EE5647670A8AD4C2BE0F9FA6E49C605ADF77B5174230AF7BD50E5D6D6D6D28CCF0A886A514CC72E51D209CC772A52EF419F6A953F3135929588EBE9B351FCA61CED78F346FE00DBB6306E5C2A4C6DFC3779AF85AB417371CF34D8387B9B30AE46D7A5FF5A655B8D8455F1B94AE736989D60A6F2FD5CADBFFBD504C5A756A2E6BB5CECC13BCA7503F6DF8B52ACE5C410997E98809DB4DC30D943DE4E812A47553DCE54844A78E36401D13F77DC650619FED88D8B3926E3D8E319C80C744779AC5D6ABE252896950917476ECE5E8FC27D5F053D6018D91B502C4787558A002B9283DA7';
  const signature = 'a4ae63dd5e7712b78f4870d0f51e294df5503d4f16c5d27ae33370981fb57f0de49f50f3d6a04666774cd984cd13972db9bf8e12bd294ef0ddc916c7c86cbae63efd7b6b97885e69760c208a40f1aecc76a90d7af5145177efce1bb55807a8d05c20b1596753ba710642fc9acdde6c160232654662c77cc4466c8257a38edb49f894e8845d0fd987b857ced88f4b62505a080bd87ef700d35d392a6e8f6fde34250c50b86fae606cb551215e8f4813239b77651d5565ad453698c071d48c31e8e526fb4a37610f64b3e1fb8e5be5898e408ad08197a0947794a530b54f84485377ce4a7488ed485ce4e5e105dd89698a472f390c3b1b76bc16b73276c4d1c81d';
  const key = forge.pki.rsa.setPublicKey(new forge.jsbn.BigInteger(modulus, 16), new forge.jsbn.BigInteger('3'));
  const digest = forge.md.sha256.create().update('hello world!').digest().getBytes();
  assert.throws(() => key.verify(digest, forge.util.hexToBytes(signature), undefined,
    { _skipPaddingChecks: true }), /ASN.1 object does not contain a valid RSASSA-PKCS1-v1_5 DigestInfo/);

  // Ephemeral test key: valid signatures must continue to verify after the backport.
  const pair = crypto.generateKeyPairSync('rsa', { modulusLength: 1024,
    privateKeyEncoding: { type: 'pkcs1', format: 'pem' },
    publicKeyEncoding: { type: 'pkcs1', format: 'pem' } });
  const privateKey = forge.pki.privateKeyFromPem(pair.privateKey);
  const publicKey = forge.pki.publicKeyFromPem(pair.publicKey);
  const md = forge.md.sha256.create().update('Zeus backport smoke');
  assert(publicKey.verify(md.digest().getBytes(), privateKey.sign(md)));
  console.log(`node-forge nested-garbage rejected; valid RSA signature accepted: ${target}`);
}
