# on-finished

[![NPM Version][npm-image]][npm-url]
[![NPM Downloads][downloads-image]][downloads-url]
[![Node.js Version][node-version-image]][node-version-url]
[![Build Status][travis-image]][travis-url]
[![Test Coverage][coveralls-image]][coveralls-url]

Execute a callback when a request closes, finishes, or errors.

## Install

```sh
$ npm install on-finished
```

## API

```js
var onFinished = require('on-finished')
```

### onFinished(res, listener)

Attach a listener to listen for the response to finish. The listener will
be invoked only once when the response finished. If the response finished
to to an error, the first argument will contain the error. If the response
has already finished, the listener will be invoked.

Listening to the end of a response would be used to close things associated
with the response, like open files.

Listener is invoked as `listener(err, res)`.

```js
onFinished(res, function (err, res) {
  // clean up open fds, etc.
  // err contains the error is request error'd
})
```

### onFinished(req, listener)

Attach a listener to listen for the request to finish. The listener will
be invoked only once when the request finished. If the request finished
to to an error, the first argument will contain the error. If the request
has already finished, the listener will be invoked.

Listening to the end of a request would be used to know when to continue
after reading the data.

Listener is invoked as `listener(err, req)`.

```js
var data = ''

req.setEncoding('utf8')
res.on('data', function (str) {
  data += str
})

onFinished(req, function (err, req) {
  // data is read unless there is err
})
```

### onFinished.isFinished(res)

Determine if `res` is already finished. This would be useful to check and
not even start certain operations if the response has already finished.

### onFinished.isFinished(req)

Determine if `req` is already finished. This would be useful to check and
not even start certain operations if the request has already finished.

### Example

The following code ensures that file descriptors are always closed
once the response finishes.

```js
var destroy = require('destroy')
var http = require('http')
var onFinished = require('on-finished')

http.createServer(function onRequest(req, res) {
  var stream = fs.createReadStream('package.json')
  stream.pipe(res)
  onFinished(res, function (err) {
    destroy(stream)
  })
})
```

## License

[MIT](LICENSE)

[npm-image]: https://img.shields.io/npm/v/on-finished.svg?style=flat
[npm-url]: https://npmjs.org/package/on-finished
[node-version-image]: https://img.shields.io/node/v/on-finished.svg?style=flat
[node-version-url]: http://nodejs.org/download/
[travis-image]: https://img.shields.io/travis/jshttp/on-finished.svg?style=flat
[travis-url]: https://travis-ci.org/jshttp/on-finished
[coveralls-image]: https://img.shields.io/coveralls/jshttp/on-finished.svg?style=flat
[coveralls-url]: https://coveralls.io/r/jshttp/on-finished?branch=master
[downloads-image]: https://img.shields.io/npm/dm/on-finished.svg?style=flat
[downloads-url]: https://npmjs.org/package/on-finished
