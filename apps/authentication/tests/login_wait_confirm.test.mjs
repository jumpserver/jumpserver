import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import vm from 'node:vm'

const template = readFileSync(new URL('../templates/authentication/login_wait_confirm.html', import.meta.url), 'utf8')
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace(/{% url '([^']+)' %}/g, (_, route) => '/' + route)
  .replace(/{% trans (['"])(.*?)\1 %}/g, (_, quote, text) => text)

function page() {
  const handlers = new Map(), requests = [], elements = new Map(), timers = new Set()
  let timerId = 0, reloads = 0
  function $(selector) {
    if (!elements.has(selector)) {
      const element = {
        visible: true, classes: new Set(), attributes: {},
        ready() { return this },
        on(event, target, callback) { handlers.set(target, callback); return this },
        show() { this.visible = true; return this },
        hide() { this.visible = false; return this },
        text(value) { this.message = value; return this },
        addClass(value) { this.classes.add(value); return this },
        removeClass(value) { this.classes.delete(value); return this },
        attr(key, value) { this.attributes[key] = value; return this },
        removeAttr(key) { delete this.attributes[key]; return this }
      }
      elements.set(selector, element)
    }
    return elements.get(selector)
  }
  const window = { location: { reload() { reloads++ } } }
  const initialLocation = window.location
  const context = vm.createContext({
    $, document: {}, window, requestApi: options => requests.push(options),
    setInterval() { const id = ++timerId; timers.add(id); return id },
    clearInterval(id) { timers.delete(id) }
  })
  vm.runInContext(script, context)
  context.interval = context.setInterval()
  context.checkInterval = context.setInterval()
  return { context, requests, $, window, initialLocation, timers,
    click: selector => handlers.get(selector)(), reloads: () => reloads }
}

test('Return waits for cancellation and ignores late approval polls and repeated clicks', () => {
  const p = page()
  p.context.doRequestAuth()
  const poll = p.requests[0]
  p.click('.btn-return')
  p.click('.btn-return')
  p.click('.btn-refresh')
  assert.deepEqual(p.requests.map(r => r.method), ['GET', 'DELETE'])
  assert.equal(p.window.location, p.initialLocation)
  assert.equal(p.reloads(), 0)
  assert.equal(p.timers.size, 0)
  poll.success({ msg: 'ok' })
  assert.equal(p.window.location, p.initialLocation)
  p.requests[1].success('')
  assert.equal(p.window.location, '/authentication:logout')
})

test('failed cancellation stays on the page and can be retried without late login redirects', () => {
  const p = page()
  p.context.doRequestAuth()
  const poll = p.requests[0]
  p.click('.btn-return')
  p.requests[1].error()
  assert.equal(p.window.location, p.initialLocation)
  assert.equal(p.$('.error-messages').visible, true)
  assert.equal(p.$('.error-messages').message, 'Unable to cancel the login request. Please try again.')
  assert.equal(p.$('.btn-return, .btn-refresh').classes.has('disabled'), false)
  poll.success({ msg: 'ok' })
  assert.equal(p.window.location, p.initialLocation)
  p.click('.btn-return')
  assert.equal(p.requests[2].method, 'DELETE')
  p.requests[2].success('')
  assert.equal(p.window.location, '/authentication:logout')
})

test('ordinary polling and manual refresh retain the previous login behavior', () => {
  const p = page()
  p.context.doRequestAuth()
  p.requests[0].success({ error: 'login_confirm_wait' })
  assert.equal(p.window.location, p.initialLocation)
  p.context.doRequestAuth()
  p.requests[1].success({ msg: 'ok' })
  assert.equal(p.window.location, '/authentication:login-guard')
  assert.equal(p.timers.size, 0)
  const refreshing = page()
  refreshing.click('.btn-refresh')
  assert.equal(refreshing.reloads(), 1)
  assert.equal(refreshing.requests.length, 0)
})
