'use strict'

const crypto = require('node:crypto')
const { inspect } = require('node:util')
const { setTimeout: wait } = require('node:timers/promises')
const { WebSocket, createWebSocketStream } = require('ws')

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

  constructor({
    endpoint,
    appId,
    appSecret,
    instanceId,
    orgId = '00000000-0000-0000-0000-000000000002',
    configurationId,
    timeout = 10000,
    source = 'jms-pam',
  }) {
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
      configurationId,
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
    if (this.#options.configurationId) result.configuration_id = this.#options.configurationId
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
    let dataObject
    try {
      dataObject = object(await response.json())
    } catch (cause) {
      throw new PAMError('ResponseError', 'The server returned invalid JSON', {
        statusCode: response.status,
        cause,
      })
    }
    if (!response.ok) {
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

  getCredential({ key, accountId, signal } = {}) {
    if ((key === undefined) === (accountId === undefined))
      throw new TypeError('Exactly one of key or accountId is required')
    requiredString(key === undefined ? accountId : key, 'selector')
    return this.#request('GET', '/credential/', { key, account_id: accountId }, credential, {
      signal,
    })
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
        if (data.configuration !== undefined && data.configuration !== null)
          object(data.configuration)
        // Agent configuration uses protocol field names, matching Python's configuration mapping.
        return { ...camelize(data), configuration: data.configuration }
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
        let lastMessage = Date.now()
        const ping = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN && Date.now() - lastMessage >= 10000) {
            socket.send(JSON.stringify({ event: 'ping' }), () => {})
          }
        }, 10000)
        try {
          for await (const frame of stream) {
            if (combined.aborted) break
            const event = object(JSON.parse(frame.toString()))
            requiredString(event.event, 'event')
            lastMessage = Date.now()
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
            yield camelize(event)
          }
        } catch {
          // Reconnect without logging response bodies, URLs or authorization material.
        } finally {
          clearInterval(ping)
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
  }
}

module.exports = { Client, PAMError, VERSION, PROTOCOL_VERSION, CONFIG_SCHEMA_VERSION }
