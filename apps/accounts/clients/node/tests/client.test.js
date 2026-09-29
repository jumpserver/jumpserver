'use strict'
const assert = require('node:assert/strict')
const { inspect } = require('node:util')
const { test, before, after } = require('node:test')
const { setTimeout: wait } = require('node:timers/promises')
const { Client, PAMError } = require('../index')
const { startServer } = require('../../tests/contract-server')
let server
before(async () => {
  server = await startServer()
})
after(async () => {
  assert.deepEqual(server.stats().failures, [])
  await server.close()
})
function client(instanceId = 'node', source = 'jms-pam') {
  return new Client({
    endpoint: server.endpoint,
    appId: 'contract-app',
    appSecret: 'contract-secret',
    instanceId,
    orgId: 'contract-org',
    configurationId: 'configuration',
    source,
  })
}

test('automatic signing, encoded selectors and typed responses', async () => {
  const sdk = client()
  try {
    for (const selector of [{ accountId: 'account' }, { key: 'db/空 格?=&' }]) {
      const item = await sdk.getCredential(selector)
      assert.equal(item.account.secret, 'DO_NOT_LOG_SECRET')
      assert.equal(item.account.secretType, 'password')
      assert.equal(item.asset.platform.type, 'postgresql')
      assert.ok(!inspect(item).includes('DO_NOT_LOG_SECRET'))
    }
    const item = await sdk.getCredential({ key: 'db' })
    assert.equal(
      (
        await sdk.confirmCredential({
          key: item.key,
          revision: item.revision,
          accountId: item.account.id,
        })
      ).revision,
      2,
    )
  } finally {
    sdk.close()
  }
})

test('invalid selectors and revisions fail before network access', () => {
  const sdk = client()
  const count = server.stats().requests.length
  assert.throws(() => sdk.getCredential({}), TypeError)
  assert.throws(() => sdk.getCredential({ key: 'db', accountId: 'account' }), TypeError)
  for (const revision of [true, '2', -1, 0])
    assert.throws(
      () => sdk.confirmCredential({ key: 'db', accountId: 'account', revision }),
      TypeError,
    )
  assert.equal(server.stats().requests.length, count)
  sdk.close()
})

test('HTTP, upgrade, malformed responses and redirects use PAMError', async () => {
  const sdk = client()
  try {
    for (const [key, code] of [
      ['forbidden', 'credential_not_authorized'],
      ['upgrade', 'client_upgrade_required'],
      ['invalid-json', 'ResponseError'],
      ['invalid-revision', 'ResponseError'],
      ['redirect', 'NetworkError'],
    ]) {
      await assert.rejects(
        sdk.getCredential({ key }),
        (error) => error instanceof PAMError && error.code === code,
      )
    }
  } finally {
    sdk.close()
  }
})

test('synchronization validates revisions and boolean flags', async () => {
  const sdk = client('node-agent', 'jms-pam-agent')
  const options = { credentials: [{ key: 'db', revision: 2 }], deliveredCredentials: [] }
  try {
    const sync = await sdk.syncAgent(options)
    assert.equal(sync.credentials[0].changed, false)
    assert.equal(sync.configuration.delivery_mode, 'socket')
    await assert.rejects(
      sdk.syncAgent({ ...options, syncError: 'invalid-flag' }),
      (error) => error.code === 'ResponseError',
    )
  } finally {
    sdk.close()
  }
})

test('command claims prevent duplicate execution and retain handler errors', async () => {
  const sdk = client()
  try {
    const [event] = await sdk.listApplicationCommands()
    let executed = 0
    assert.equal((await sdk.executeApplicationCommand(event, () => executed++)).status, 'success')
    assert.equal(executed, 1)
    assert.equal(
      (await sdk.executeApplicationCommand({ ...event, commandId: 'duplicate' }, () => executed++))
        .accepted,
      false,
    )
    assert.equal(executed, 1)
    const failure = new Error('business failure')
    await assert.rejects(
      sdk.executeApplicationCommand({ ...event, commandId: 'report-failure' }, () => {
        throw failure
      }),
      (error) => error === failure,
    )
  } finally {
    sdk.close()
  }
})

test(
  'event reconnection restores snapshot and sends receipts only for business events',
  { timeout: 6000 },
  async () => {
    const sdk = client('node-events')
    const events = []
    try {
      for await (const event of sdk.watchCredentialEvents()) {
        events.push(event)
        if (events.length === 4) break
      }
      assert.deepEqual(
        events.map((event) => event.event),
        ['snapshot', 'credential.updated', 'future.notification', 'snapshot'],
      )
      assert.equal(events[3].credentials[0].revision, 3)
      assert.equal(events[2].futurePayload.notice, 'preserved')
      await wait(20)
      const received = server
        .stats()
        .receipts.filter((receipt) => receipt.instance === 'node-events')
        .map((receipt) => receipt.eventId)
      assert.ok(received.includes('updated-1'))
      assert.ok(received.includes('future-1'))
      assert.ok(received.every((id) => !id.includes('snapshot')))
    } finally {
      sdk.close()
    }
  },
)

test(
  'cancellation and close stop active streams; clone remains independent',
  { timeout: 4000 },
  async () => {
    const sdk = client('node-stop')
    const clone = sdk.clone()
    const abort = new AbortController()
    const stream = sdk.watchCredentialEvents({ signal: abort.signal })
    assert.equal((await stream.next()).value.event, 'snapshot')
    abort.abort()
    await stream.return()
    sdk.close()
    await assert.rejects(sdk.getCredential({ key: 'db' }), /closed/)
    assert.equal((await clone.getCredential({ key: 'db' })).revision, 2)
    clone.close()
  },
)
