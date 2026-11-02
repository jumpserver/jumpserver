// Run with: node --test apps/authentication/tests/test_vctks_signing.cjs
const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const adapter = fs.readFileSync(path.join(__dirname, '../backends/ukey/vendors/ji_da/vctks_certificate.js'), 'utf8')
const template = fs.readFileSync(path.join(__dirname, '../templates/authentication/login_ukey.html'), 'utf8')
const window = { atob: value => atob(value) }
vm.runInNewContext(adapter, { window })

function tlv(tag, value) {
  const data = Buffer.isBuffer(value) ? value : Buffer.concat(value)
  const size = data.length < 128 ? [data.length] : [0x82, data.length >> 8, data.length & 255]
  // Minimal DER length encoding.
  if (data.length >= 128 && data.length < 256) size.splice(0, 2, 0x81)
  return Buffer.concat([Buffer.from([tag, ...size]), data])
}
const sequence = (...items) => tlv(0x30, items)
const oid = hex => tlv(6, Buffer.from(hex, 'hex'))
const nullValue = tlv(5, [])
const sm2 = '2a811ccf5501822d'
const ec = '2a8648ce3d0201'
const rsa = '2a864886f70d010101'
const algorithm = (id, param) => sequence(oid(id), ...(param ? [param] : []))

// Structural certificates exercise SPKI selection only; cryptography is tested in Python/GmSSL.
function certificate(publicAlgorithm, signatureAlgorithm = algorithm(rsa, nullValue), version = true) {
  const body = [
    ...(version ? [tlv(0xa0, [tlv(2, Buffer.from([2]))])] : []),
    tlv(2, Buffer.from([1])), signatureAlgorithm,
    sequence(), sequence(), sequence(),
    sequence(publicAlgorithm, tlv(3, Buffer.from([0, 4, 1, 2, 3])))
  ]
  return sequence(sequence(...body), signatureAlgorithm, tlv(3, Buffer.from([0, 1]))).toString('base64')
}
const rsaCert = certificate(algorithm(rsa, nullValue))
const sm2Cert = certificate(algorithm(ec, oid(sm2)))

test('digest follows SPKI, not issuer signature algorithm or certificate version', () => {
  assert.equal(window.VCTKSCertificateDigest(rsaCert), 4)
  assert.equal(window.VCTKSCertificateDigest(sm2Cert), 1)
  assert.equal(window.VCTKSCertificateDigest(certificate(algorithm(sm2))), 1)
  assert.equal(window.VCTKSCertificateDigest(certificate(algorithm(sm2, nullValue))), 1)
  assert.equal(window.VCTKSCertificateDigest(certificate(algorithm(rsa), algorithm(sm2), false)), 4)
  assert.equal(window.VCTKSCertificateDigest(' \n' + sm2Cert + '\r\n'), 1)
})

test('unknown algorithms and malformed certificates fail without guessing', () => {
  const der = Buffer.from(rsaCert, 'base64')
  for (const value of [
    '', null, 'not-a-certificate', rsaCert + '!!!!',
    certificate(algorithm(ec, oid('2a8648ce3d030107'))),
    certificate(algorithm(rsa, oid(sm2))),
    certificate(algorithm('2b6570')),
    Buffer.concat([der, Buffer.from([0])]).toString('base64'),
    der.subarray(0, der.length - 1).toString('base64'),
    Buffer.from([0x30, 0x80, 0, 0]).toString('base64'),
    'A'.repeat(32772)
  ]) {
    assert.throws(() => window.VCTKSCertificateDigest(value))
  }
})

function loginRunner() {
  let source = template.slice(template.indexOf('(function () {'), template.indexOf('    /* ── Main init'))
  source = source.replace(/{% trans "([^"]*)" %}/g, '$1').replace(/{{[^}]+}}/g, '')
  source += '\nwindow.runStepsForTest = runSteps;\n}());'
  const browser = { atob: value => atob(value) }
  const sandbox = { window: browser, document: { getElementById: () => ({}) } }
  vm.runInNewContext(adapter, sandbox)
  vm.runInNewContext(source, sandbox)
  return browser.runStepsForTest
}

test('the actual login executor overrides CA-derived digest using the current certificate', async () => {
  const runSteps = loginRunner()
  for (const [cert, expected, configured] of [[rsaCert, 4, 1], [sm2Cert, 1, 4]]) {
    const calls = []
    const api = { UKey_P7SignAttach: (...args) => { calls.push(args); return 'signature' } }
    const ctx = { ukey: { cert }, vars: {}, config: { digestAlg: configured }, challenge: { code: 'challenge' } }
    await runSteps([{
      call: 'UKey_P7SignAttach', args: ['{{ config.digestAlg }}', '{{ challenge.code }}'],
      digest_certificate: '{{ ukey.cert }}', register: 'vars.signature'
    }], api, ctx)
    assert.deepEqual(calls, [[expected, 'challenge']])
    assert.equal(ctx.vars.signature, 'signature')
  }
})

test('invalid signing certificate prevents the SDK signing call', async () => {
  let calls = 0
  await assert.rejects(loginRunner()([{
    call: 'UKey_P7SignAttach', args: [1, 'challenge'], digest_certificate: '{{ ukey.cert }}'
  }], { UKey_P7SignAttach: () => { calls++ } }, { ukey: { cert: 'broken' } }))
  assert.equal(calls, 0)
})

test('builtin signing steps retain their configured arguments', async () => {
  let received
  await loginRunner()([{ call: 'UKey_SignData', args: [4, 'challenge'] }], {
    UKey_SignData: (...args) => { received = args }
  }, {})
  assert.deepEqual(received, [4, 'challenge'])
})
