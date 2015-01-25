/*!
 * finalhandler
 * Copyright(c) 2014 Douglas Christopher Wilson
 * MIT Licensed
 */

/**
 * Module dependencies.
 */

var debug = require('debug')('finalhandler')
var escapeHtml = require('escape-html')
var http = require('http')
var onFinished = require('on-finished')

/**
 * Variables.
 */

/* istanbul ignore next */
var defer = typeof setImmediate === 'function'
  ? setImmediate
  : function(fn){ process.nextTick(fn.bind.apply(fn, arguments)) }
var isFinished = onFinished.isFinished

/**
 * Module exports.
 */

module.exports = finalhandler

/**
 * Final handler:
 *
 * @param {Request} req
 * @param {Response} res
 * @param {Object} [options]
 * @return {Function}
 * @api public
 */

function finalhandler(req, res, options) {
  options = options || {}

  // get environment
  var env = options.env || process.env.NODE_ENV || 'development'

  // get error callback
  var onerror = options.onerror

  return function (err) {
    var msg

    // ignore 404 on in-flight response
    if (!err && res._header) {
      debug('cannot 404 after headers sent')
      return
    }

    // unhandled error
    if (err) {
      // default status code to 500
      if (!res.statusCode || res.statusCode < 400) {
        res.statusCode = 500
      }

      // respect err.status
      if (err.status) {
        res.statusCode = err.status
      }

      // production gets a basic error message
      var msg = env === 'production'
        ? http.STATUS_CODES[res.statusCode]
        : err.stack || err.toString()
      msg = escapeHtml(msg)
        .replace(/\n/g, '<br>')
        .replace(/  /g, ' &nbsp;') + '\n'
    } else {
      res.statusCode = 404
      msg = 'Cannot ' + escapeHtml(req.method) + ' ' + escapeHtml(req.originalUrl || req.url) + '\n'
    }

    debug('default %s', res.statusCode)

    // schedule onerror callback
    if (err && onerror) {
      defer(onerror, err, req, res)
    }

    // cannot actually respond
    if (res._header) {
      return req.socket.destroy()
    }

    send(req, res, res.statusCode, msg)
  }
}

/**
 * Send response.
 *
 * @param {IncomingMessage} req
 * @param {OutgoingMessage} res
 * @param {number} status
 * @param {string} body
 * @api private
 */

function send(req, res, status, body) {
  function write() {
    res.statusCode = status

    // security header for content sniffing
    res.setHeader('X-Content-Type-Options', 'nosniff')

    // standard headers
    res.setHeader('Content-Type', 'text/html; charset=utf-8')
    res.setHeader('Content-Length', Buffer.byteLength(body, 'utf8'))

    if (req.method === 'HEAD') {
      res.end()
      return
    }

    res.end(body, 'utf8')
  }

  if (isFinished(req)) {
    write()
    return
  }

  // unpipe everything from the request
  unpipe(req)

  // flush the request
  onFinished(req, write)
  req.resume()
}

/**
 * Unpipe everything from a stream.
 *
 * @param {Object} stream
 * @api private
 */

/* istanbul ignore next: implementation differs between versions */
function unpipe(stream) {
  if (typeof stream.unpipe === 'function') {
    // new-style
    stream.unpipe()
    return
  }

  // Node.js 0.8 hack
  var listener
  var listeners = stream.listeners('close')

  for (var i = 0; i < listeners.length; i++) {
    listener = listeners[i]

    if (listener.name !== 'cleanup' && listener.name !== 'onclose') {
      continue
    }

    // invoke the listener
    listener.call(stream)
  }
}
