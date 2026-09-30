'use strict'
const assert = require('node:assert/strict')
const { inspect } = require('node:util')
const { test, before, after } = require('node:test')
const { setTimeout: wait } = require('node:timers/promises')
const { Client, PAMError } = require('../index')
const { startServer } = require('../../tests/contract-server')
let server
before(async () => { server = await startServer() })
after(async () => { assert.deepEqual(server.stats().failures, []); await server.close() })
function client(instanceId, options = {}) {
  return new Client({ endpoint: server.endpoint, appId: 'contract-app', appSecret: 'contract-secret',
    instanceId, orgId: 'contract-org', ...options })
}

test('retained credentials handle 5xx and response body timeout, preserving secret redaction', async () => {
  for (const fault of ['503', 'timeout']) {
    const sdk = client(`node-cache-${fault}`, { timeout: 300 })
    try {
      const key = `cache-${fault}`
      const live = await sdk.getCredential({ key })
      assert.equal(live.fromLocal, false)
      live.account.secret = 'consumer mutation'
      const retained = await sdk.getCredential({ key })
      assert.equal(retained.fromLocal, true)
      assert.equal(retained.account.secret, 'DO_NOT_LOG_SECRET')
      assert.ok(!inspect(retained).includes('DO_NOT_LOG_SECRET'))
      retained.account.secret = 'another mutation'
      assert.equal((await sdk.getCredential({ key })).account.secret, 'DO_NOT_LOG_SECRET')
      await assert.rejects(sdk.getCredential({ key, allowLocalFallback: false }), PAMError)
      const canceled = AbortSignal.abort()
      await assert.rejects(sdk.getCredential({ key, signal: canceled }), PAMError)
      const clone = sdk.clone()
      try { await assert.rejects(clone.getCredential({ key }), PAMError) } finally { clone.close() }
    } finally { sdk.close() }
  }
})

test('authorization, upgrade, malformed success fail explicitly', async () => {
  for (const fault of ['401', '403', '404', '426', 'revoked', 'invalid']) {
    const sdk = client(`node-cache-${fault}`)
    try {
      const key = `cache-${fault}`
      await sdk.getCredential({ key })
      await assert.rejects(sdk.getCredential({ key }), PAMError)
    } finally { sdk.close() }
  }

})

test('snapshot scope removes unauthorized credentials before exposing the event', async () => {
  const sdk = client('node-cache-scope')
  try {
    await sdk.getCredential({ key: 'cache-503' })
    for await (const event of sdk.watchCredentialEvents()) {
      assert.equal(event.event, 'snapshot')
      await assert.rejects(sdk.getCredential({ key: 'cache-503' }), PAMError)
      break
    }
  } finally { sdk.close() }
})

test('managed listener reconnects and awaits async hooks serially', async () => {
  const sdk = client('hooks-node')
  const revisions = [], errors = []
  let active = 0
  sdk.onCredentialChanged = async (credential) => {
    assert.equal(active++, 0); assert.equal(credential.fromLocal, false)
    await wait(15); revisions.push(credential.revision); active--
    if (credential.revision >= 3) await sdk.stopEvents()
  }
  sdk.onEventError = (error) => errors.push(error)
  const subscription = sdk.startEvents({ signal: AbortSignal.timeout(5000) })
  try {
    assert.throws(() => sdk.startEvents(), /already running/)
    await subscription.done
    assert.ok(revisions.includes(2)); assert.ok(revisions.includes(3)); assert.deepEqual(errors, [])
    assert.equal(subscription.running, false)
  } finally { sdk.close(); await subscription.stop() }
})

test('failed credential hook retries while idle and can close its own client', async () => {
  const sdk = client('retry-node')
  let calls = 0, reports = 0
  sdk.onCredentialChanged = async () => {
    if (++calls === 1) throw new Error('temporary failure')
    sdk.close()
  }
  sdk.onEventError = () => { reports++ }
  try {
    await sdk.watchEvents({ signal: AbortSignal.timeout(4000) })
    assert.equal(calls, 2); assert.equal(reports, 1)
  } finally { sdk.close() }
})

test('slow business hook keeps reader active; external stop waits for the hook', async () => {
  const sdk = client('hooks-node-slow')
  let entered, release
  const started = new Promise((resolve) => { entered = resolve })
  const unblock = new Promise((resolve) => { release = resolve })
  sdk.onCredentialChanged = async () => { entered(); await unblock }
  const subscription = sdk.startEvents({ signal: AbortSignal.timeout(5000) })
  try {
    await started
    for (let i = 0; i < 100 && (server.stats().connections.get('hooks-node-slow') || 0) < 2; i++) await wait(25)
    assert.ok(server.stats().connections.get('hooks-node-slow') >= 2)
    let stopped = false
    const stopping = subscription.stop().then(() => { stopped = true })
    await wait(10); assert.equal(stopped, false)
    release(); await stopping; assert.equal(stopped, true)
  } finally { release(); sdk.close(); await subscription.stop() }
})

test('managed refresh requires a live response and older events preserve the newer retry', async () => {
  const sdk = client('node-hooks-unit')
  let calls = 0, errors = 0, fetches = 0
  sdk.watchCredentialEvents = async function* () {
    yield { event: 'credential.updated', credentialMode: 'subscription', credentialKey: 'db:account', accountId: 'account', revision: 3 }
    yield { event: 'credential.updated', credentialMode: 'subscription', credentialKey: 'db:account', accountId: 'account', revision: 2 }
  }
  sdk.getCredential = async (options) => { fetches++; assert.equal(options.allowLocalFallback, false); return { revision: 2 } }
  sdk.onCredentialChanged = () => { calls++ }
  sdk.onEventError = () => { errors++ }
  try { await sdk.watchEvents(); assert.equal(calls, 0); assert.equal(errors, 1); assert.equal(fetches, 1) } finally { sdk.close() }
})

function control(instance, options) {
  const url = new URL(server.endpoint.replace('/prefix', '') + '/__control')
  url.search = new URLSearchParams({ instance, ...options }).toString()
  return fetch(url).then((response) => response.json())
}

test('application pull requires the live API after a successful fetch', async () => {
  const id = 'node-live-pull'
  const sdk = client(id)
  try {
    await sdk.getCredential({ accountId: 'account' })
    await control(id, { fault: 503 })
    await assert.rejects(sdk.getCredential({ accountId: 'account' }), PAMError)
  } finally { sdk.close() }
})

test('policy revocation removes subscription aliases during a backend outage', async () => {
  const id = 'latest-node-revoked-alias'
  const sdk = client(id)
  const events = sdk.watchCredentialEvents({ signal: AbortSignal.timeout(5000) })
  try {
    assert.equal((await events.next()).value.event, 'snapshot')
    await sdk.getCredential({ key: 'db:account' })
    await control(id, { fault: 503 })
    assert.equal((await sdk.getCredential({ key: 'db:account' })).fromLocal, true)
    await control(id, { event: 'credential.revoked' })
    for await (const event of events) if (event.event === 'credential.revoked') break
    await assert.rejects(sdk.getCredential({ key: 'db:account' }), PAMError)
  } finally { sdk.close(); await events.return() }
})

test('latest credentials survive elapsed time and are refreshed automatically by events', async (t) => {
  const id = 'latest-node-events'
  const sdk = client(id)
  let initial, updated
  const ready = new Promise((resolve) => {initial = resolve})
  const refreshed = new Promise((resolve) => {updated = resolve})
  sdk.onCredentialChanged = async (credential) => {
    assert.equal(credential.fromLocal, false)
    if (credential.revision >= 3) updated(); else initial()
  }
  sdk.onEventError = () => {}
  const sub = sdk.startEvents({signal: AbortSignal.timeout(5000)})
  try {
    await ready
    await control(id, {revision: 3, event: 'credential.updated'})
    await refreshed
    await control(id, {fault: 503})
    const {performance} = require('node:perf_hooks')
    const clock = performance.now()
    t.mock.method(performance, 'now', () => clock + 86400000)
    const retained = await sdk.getCredential({key: 'db'})
    assert.equal(retained.fromLocal, true)
    assert.equal(retained.revision, 3)
    assert.equal(retained.account.secret, 'LATEST_SECRET_3')
    await control(id, {fault: 0, revision: 4})
    assert.equal((await sdk.getCredential({key: 'db'})).revision, 4)
    await control(id, {revision: 2})
    await assert.rejects(sdk.getCredential({key: 'db'}), PAMError)
    await control(id, {fault: 503})
    assert.equal((await sdk.getCredential({key: 'db'})).revision, 4)
  } finally {sdk.close(); await sub.stop()}
})
