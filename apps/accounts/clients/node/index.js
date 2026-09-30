'use strict'

const crypto = require('node:crypto')
const { inspect } = require('node:util')
const { performance } = require('node:perf_hooks')
const { setTimeout: wait } = require('node:timers/promises')
const { WebSocket, createWebSocketStream } = require('ws')
const { EventSubscription } = require('./event-dispatcher')

const VERSION = '1.0.0'
const PROTOCOL_VERSION = 1
const CONFIG_SCHEMA_VERSION = 1
const CLIENT_PATH = '/api/v1/accounts/credential-client'
const SIGNATURE_HEADERS = [
  '(request-target)',
  'accept',
  'date',
  'digest',
  'x-jms-request-id',
  'x-jms-org',
  'x-jms-client-version',
  'x-jms-protocol-version',
  'x-jms-config-schema-version',
]

class PAMError extends Error {
  constructor(code, message, { statusCode, detail, requestId, cause } = {}) {
    super(`[${code}] ${detail || message}`, { cause })
    this.name = 'PAMError'
    this.code = code
    this.statusCode = statusCode
    this.detail = detail
    this.requestId = requestId
  }
}

function requiredString(value, name) {
  if (typeof value !== 'string' || !value) throw new TypeError(`${name} must be a non-empty string`)
  return value
}

function revision(value, minimum = 0) {
  if (!Number.isSafeInteger(value) || value < minimum) throw new TypeError('Invalid revision')
  return value
}

function object(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new TypeError('Expected an object')
  return value
}

function camelize(value) {
  if (Array.isArray(value)) return value.map(camelize)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase()),
      camelize(item),
    ]),
  )
}

function credential(data) {
  object(data)
  for (const name of ['key']) requiredString(data[name], name)
  revision(data.revision)
  for (const [item, names] of [
    [data.asset, ['id', 'name', 'address']],
    [data.asset?.platform, ['id', 'name', 'category', 'type']],
    [data.account, ['id', 'name', 'username', 'secret_type', 'secret']],
  ]) {
    object(item)
    for (const name of names) requiredString(item[name], name)
  }
  const result = camelize(data)
  result.fromLocal = false
  Object.defineProperty(result.account, inspect.custom, {
    value: () => ({ ...result.account, secret: '[REDACTED]' }),
  })
  return result
}

function copyCredential(value, fromLocal) {
  const result = structuredClone(value)
  result.fromLocal = fromLocal
  Object.defineProperty(result.account, inspect.custom, {
    value: () => ({ ...result.account, secret: '[REDACTED]' }),
  })
  return result
}

function commandResult(data) {
  if (typeof data.accepted !== 'boolean') throw new TypeError('accepted must be a boolean')
  requiredString(data.status, 'status')
  return camelize(data)
}

/** One application replica. Each request and WebSocket reconnect gets a fresh signature. */
class Client {
  #options
  #closed = new AbortController()
  #streams = new Set()
  #eventSubscription
  #latestCredentials = new Map()
  #credentialGeneration = 0

  constructor({
    endpoint,
    appId,
    appSecret,
    instanceId,
    orgId = '00000000-0000-0000-0000-000000000002',
    timeout = 10000,
    source = 'jms-pam',
  }) {
    if (Object.hasOwn(arguments[0], 'configurationId'))
      throw new TypeError('configurationId was removed; use application identity and instanceId')
    requiredString(endpoint, 'endpoint')
    const url = new URL(endpoint)
    if (
      !['http:', 'https:'].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      throw new TypeError('endpoint must be an HTTP(S) URL without credentials, query or fragment')
    }
    requiredString(appId, 'appId')
    requiredString(appSecret, 'appSecret')
    requiredString(instanceId, 'instanceId')
    if (instanceId.trim() !== instanceId || instanceId.length > 128)
      throw new TypeError('Invalid instanceId')
    if (!Number.isSafeInteger(timeout) || timeout <= 0)
      throw new TypeError('timeout must be positive milliseconds')
    this.#options = {
      endpoint: endpoint.replace(/\/+$/, ''),
      appId,
      appSecret,
      instanceId,
      orgId,
      timeout,
      source,
    }
  }

  #url(path, params = {}) {
    const url = new URL(this.#options.endpoint + path)
    for (const [name, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(name, value)
    }
    return url
  }

  #identity(data) {
    const result = { ...data, instance_id: this.#options.instanceId }
    return result
  }

  #headers(method, url, body = '') {
    const options = this.#options
    const headers = {
      accept: 'application/json',
      date: new Date().toUTCString(),
      digest: 'SHA-256=' + crypto.createHash('sha256').update(body).digest('base64'),
      'x-jms-request-id': crypto.randomUUID(),
      'x-jms-org': options.orgId,
      'x-jms-client-version': VERSION,
      'x-jms-protocol-version': String(PROTOCOL_VERSION),
      'x-jms-config-schema-version':
        options.source === 'jms-pam-agent' ? String(CONFIG_SCHEMA_VERSION) : '0',
      'x-source': options.source,
    }
    const signing = SIGNATURE_HEADERS.map(
      (name) =>
        `${name}: ${
          name === '(request-target)'
            ? method.toLowerCase() + ' ' + url.pathname + url.search
            : headers[name]
        }`,
    ).join('\n')
    const signature = crypto
      .createHmac('sha256', options.appSecret)
      .update(signing)
      .digest('base64')
    headers.authorization = `Signature keyId="${options.appId}",algorithm="hmac-sha256",signature="${signature}",headers="${SIGNATURE_HEADERS.join(' ')}"`
    return headers
  }

  async #request(method, path, data, parse, { signal } = {}) {
    if (this.#closed.signal.aborted) throw new Error('Client is closed')
    data = this.#identity(data)
    const url = this.#url(CLIENT_PATH + path, method === 'GET' ? data : {})
    const body = method === 'GET' ? undefined : JSON.stringify(data)
    const headers = this.#headers(method, url, body)
    if (body !== undefined) headers['content-type'] = 'application/json'
    const signals = [this.#closed.signal, AbortSignal.timeout(this.#options.timeout)]
    if (signal) signals.push(signal)
    let response
    try {
      response = await fetch(url, {
        method,
        headers,
        body,
        redirect: 'error',
        signal: AbortSignal.any(signals),
      })
    } catch (cause) {
      throw new PAMError('NetworkError', 'HTTP request failed', { cause })
    }
    if ([401, 403, 404, 426].includes(response.status)) {
      this.#latestCredentials.clear()
      this.#credentialGeneration++
    }
    let dataObject
    try {
      dataObject = await response.json()
    } catch (cause) {
      // A timeout or dropped connection can occur after the response headers.
      const invalid = cause instanceof SyntaxError
      throw new PAMError(invalid ? 'ResponseError' : 'NetworkError',
        invalid ? 'The server returned invalid JSON' : 'HTTP response failed', {
        statusCode: response.status,
        cause,
      })
    }
    try {
      dataObject = object(dataObject)
    } catch (cause) {
      throw new PAMError('ResponseError', 'The server response must be a JSON object', {
        statusCode: response.status, cause,
      })
    }
    if (!response.ok) {
      if (response.status === 400 && dataObject.code === 'credential_not_found') {
        this.#latestCredentials.clear(); this.#credentialGeneration++
      }
      throw new PAMError(
        typeof dataObject.code === 'string' && dataObject.code ? dataObject.code : 'HTTPError',
        'HTTP request failed',
        {
          statusCode: response.status,
          detail: typeof dataObject.detail === 'string' ? dataObject.detail : undefined,
          requestId: typeof dataObject.request_id === 'string' ? dataObject.request_id : undefined,
        },
      )
    }
    try {
      return parse(dataObject)
    } catch (cause) {
      throw new PAMError('ResponseError', 'The server returned an invalid response', {
        statusCode: response.status,
        cause,
      })
    }
  }

  getCredential({ key, accountId, signal, allowLocalFallback = true } = {}) {
    if ((key === undefined) === (accountId === undefined))
      throw new TypeError('Exactly one of key or accountId is required')
    requiredString(key === undefined ? accountId : key, 'selector')
    if (typeof allowLocalFallback !== 'boolean') throw new TypeError('allowLocalFallback must be boolean')
    return this.#getCredential({ key, accountId, signal, allowLocalFallback })
  }

  async #getCredential({ key, accountId, signal, allowLocalFallback }) {
    const selector = key === undefined ? `account:${accountId}` : `key:${key}`
    const generation = this.#credentialGeneration
    try {
      const value = await this.#request('GET', '/credential/', { key, account_id: accountId }, credential, { signal })
      if (!this.#closed.signal.aborted && generation === this.#credentialGeneration) {
        const latest = this.#latestCredentials.get(selector)
        if (latest && value.revision < latest.revision)
          throw new PAMError('ResponseError', 'Credential revision moved backwards', { statusCode: 200 })
        this.#latestCredentials.set(selector, copyCredential(value, false))
      }
      return value
    } catch (error) {
      const denied = [401, 403, 404].includes(error.statusCode) || error.code === 'client_upgrade_required'
        || (error.statusCode === 400 && error.code === 'credential_not_found')
      const temporary = error instanceof PAMError && (error.code === 'NetworkError'
        || (error.statusCode >= 500 && error.statusCode < 600))
      if (denied) { this.#latestCredentials.clear(); this.#credentialGeneration++ }
      const latest = this.#latestCredentials.get(selector)
      if (allowLocalFallback && key !== undefined && temporary && !denied && !signal?.aborted && !this.#closed.signal.aborted && latest)
        return copyCredential(latest, true)
      throw error
    }
  }

  #reconcileLatestCredentials(event) {
    if (!['snapshot', 'credential.revoked', 'configuration.updated'].includes(event.event)) return
    this.#credentialGeneration++
    if (event.event === 'configuration.updated') return
    if (event.event !== 'snapshot') {
      const rawKey = event.credentialKey || event.key
      const key = typeof rawKey === 'string' && rawKey ? rawKey : undefined
      const accountId = typeof event.accountId === 'string' && event.accountId ? event.accountId : undefined
      if (!key && !accountId) this.#latestCredentials.clear()
      else for (const [selector, credential] of this.#latestCredentials)
        if ((key && (selector === `key:${key}` || credential.key === key || credential.key.startsWith(`${key}:`)))
          || (accountId && (!key || key.startsWith('account:'))
            && (selector === `account:${accountId}` || credential.account.id === accountId)))
          this.#latestCredentials.delete(selector)
      return
    }
    if (!Array.isArray(event.credentials)) {
      this.#latestCredentials.clear()
      return
    }
    const keys = new Set(event.credentials.map((item) => item?.credentialKey || item?.key))
    for (const selector of this.#latestCredentials.keys())
      if (selector.startsWith('key:') && !keys.has(selector.slice(4)))
        this.#latestCredentials.delete(selector)
  }

  confirmCredential({ key, revision: value, accountId, signal }) {
    requiredString(key, 'key')
    requiredString(accountId, 'accountId')
    revision(value, 1)
    return this.#request(
      'POST',
      '/confirm/',
      { key, revision: value, account_id: accountId },
      (data) => {
        requiredString(data.key, 'key')
        revision(data.revision)
        return camelize(data)
      },
      { signal },
    )
  }

  syncAgent({
    credentials,
    deliveredCredentials,
    configDigest = '',
    syncStatus = '',
    syncError = '',
    signal,
  }) {
    const revisions = (values) => {
      if (!Array.isArray(values)) throw new TypeError('Known revisions must be an array')
      return values.map((item) => ({
        key: requiredString(item.key, 'key'),
        revision: revision(item.revision),
      }))
    }
    return this.#request(
      'POST',
      '/agent/sync/',
      {
        credentials: revisions(credentials),
        delivered_credentials: revisions(deliveredCredentials),
        config_digest: configDigest,
        sync_status: syncStatus,
        sync_error: syncError,
      },
      (data) => {
        requiredString(data.config_digest, 'config_digest')
        requiredString(data.date_last_synced, 'date_last_synced')
        if (!Array.isArray(data.credentials) || !Array.isArray(data.removed_keys))
          throw new TypeError('Invalid synchronization metadata')
        for (const item of data.credentials) {
          requiredString(item.key, 'key')
          revision(item.revision)
          if (typeof item.available !== 'boolean' || typeof item.changed !== 'boolean')
            throw new TypeError('Invalid revision flags')
        }
        if (new Set(data.credentials.map((item) => item.key)).size !== data.credentials.length)
          throw new TypeError('Duplicate revision keys')
        data.removed_keys.forEach((key) => requiredString(key, 'removed key'))
        if (data.scope !== undefined && data.scope !== null)
          object(data.scope)
        // Agent scope uses protocol field names, matching Python's scope mapping.
        return { ...camelize(data), scope: data.scope }
      },
      { signal },
    )
  }

  listApplicationCommands({ signal } = {}) {
    return this.#request(
      'GET',
      '/commands/',
      {},
      (data) => {
        if (!Array.isArray(data.commands)) throw new TypeError('commands must be an array')
        data.commands.forEach(object)
        return camelize(data.commands)
      },
      { signal },
    )
  }

  reportApplicationCommandResult({ commandId, status, errorCode, signal }) {
    requiredString(commandId, 'commandId')
    if (!['running', 'success', 'failed'].includes(status))
      throw new TypeError('Invalid command status')
    return this.#request(
      'POST',
      '/command-result/',
      { command_id: commandId, status, error_code: errorCode },
      commandResult,
      { signal },
    )
  }

  async executeApplicationCommand(event, handler, options = {}) {
    const claim = await this.reportApplicationCommandResult({
      commandId: event.commandId,
      status: 'running',
      ...options,
    })
    if (!claim.accepted) return claim
    try {
      await handler(event)
    } catch (error) {
      try {
        await this.reportApplicationCommandResult({
          commandId: event.commandId,
          status: 'failed',
          errorCode: 'execution_failed',
          ...options,
        })
      } catch {}
      throw error
    }
    return this.reportApplicationCommandResult({
      commandId: event.commandId,
      status: 'success',
      ...options,
    })
  }

  startEvents({ signal } = {}) {
    if (this.#closed.signal.aborted) throw new Error('Client is closed')
    if (this.#eventSubscription?.running) throw new Error('An event listener is already running')
    this.#eventSubscription = new EventSubscription(this, { signal, clientSignal: this.#closed.signal })
    return this.#eventSubscription
  }

  async watchEvents(options = {}) {
    await this.startEvents(options).done
  }

  async stopEvents() {
    await this.#eventSubscription?.stop()
  }

  onEvent(event, options) {}
  onCredentialChanged(credential, options) {}
  onCredentialRevoked(event, options) {}
  onEventError(error, event) {
    console.warn('Credential event handler failed:', error?.constructor?.name || 'Error')
  }

  async *watchCredentialEvents({ signal } = {}) {
    if (this.#closed.signal.aborted) throw new Error('Client is closed')
    const stop = new AbortController()
    this.#streams.add(stop)
    const signals = [stop.signal, this.#closed.signal]
    if (signal) signals.push(signal)
    const combined = AbortSignal.any(signals)
    let delay = 1000
    try {
      while (!combined.aborted) {
        const url = this.#url('/ws/accounts/credential-events/', this.#identity({}))
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
        const socket = new WebSocket(url, {
          headers: { ...this.#headers('GET', url), 'x-jms-event-receipts': '1' },
          handshakeTimeout: this.#options.timeout,
          followRedirects: false,
          maxPayload: 16 * 1024 * 1024,
        })
        const stream = createWebSocketStream(socket, {
          readableObjectMode: true,
          highWaterMark: 16,
        })
        const terminate = () => socket.terminate()
        combined.addEventListener('abort', terminate, { once: true })
        if (combined.aborted) terminate()
        let lastMessage = performance.now()
        const received = () => { lastMessage = performance.now() }
        socket.on('message', received)
        const ping = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN && performance.now() - lastMessage >= 30000) {
            socket.terminate()
          } else if (socket.readyState === WebSocket.OPEN && performance.now() - lastMessage >= 10000) {
            socket.send(JSON.stringify({ event: 'ping' }), () => {})
          }
        }, 10000)
        try {
          for await (const frame of stream) {
            if (combined.aborted) break
            const event = object(JSON.parse(frame.toString()))
            requiredString(event.event, 'event')
            delay = 1000
            if (event.event === 'pong') continue
            if (
              event.event !== 'snapshot' &&
              event.event_id &&
              socket.readyState === WebSocket.OPEN
            ) {
              await new Promise((resolve) =>
                socket.send(JSON.stringify({ event: 'received', event_id: event.event_id }), () =>
                  resolve(),
                ),
              )
            }
            const message = camelize(event)
            this.#reconcileLatestCredentials(message)
            yield message
          }
        } catch {
          // Reconnect without logging response bodies, URLs or authorization material.
        } finally {
          clearInterval(ping)
          socket.off('message', received)
          combined.removeEventListener('abort', terminate)
          stream.destroy()
          socket.terminate()
        }
        if (!combined.aborted) {
          try {
            await wait(delay, undefined, { signal: combined })
          } catch {}
          delay = Math.min(delay * 2, 30000)
        }
      }
    } finally {
      stop.abort()
      this.#streams.delete(stop)
    }
  }

  clone() {
    return new Client(this.#options)
  }

  close() {
    this.#closed.abort()
    for (const stream of this.#streams) stream.abort()
    this.#latestCredentials.clear()
    this.#credentialGeneration++
  }
}

module.exports = { Client, PAMError, VERSION, PROTOCOL_VERSION, CONFIG_SCHEMA_VERSION }
