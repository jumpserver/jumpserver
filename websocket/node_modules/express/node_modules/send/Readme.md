# send

[![NPM Version][npm-image]][npm-url]
[![NPM Downloads][downloads-image]][downloads-url]
[![Build Status][travis-image]][travis-url]
[![Test Coverage][coveralls-image]][coveralls-url]
[![Gittip][gittip-image]][gittip-url]

  Send is Connect's `static()` extracted for generalized use, a streaming static file
  server supporting partial responses (Ranges), conditional-GET negotiation, high test coverage, and granular events which may be leveraged to take appropriate actions in your application or framework.

## Installation

```bash
$ npm install send
```

## API

```js
var send = require('send')
```

### send(req, path, [options])

Create a new `SendStream` for the given path to send to a `res`. The `req` is
the Node.js HTTP request and the `path` is a urlencoded path to send (urlencoded,
not the actual file-system path).

#### Options

##### dotfiles

  Set how "dotfiles" are treated when encountered. A dotfile is a file
  or directory that begins with a dot ("."). Note this check is done on
  the path itself without checking if the path actually exists on the
  disk. If `root` is specified, only the dotfiles above the root are
  checked (i.e. the root itself can be within a dotfile when when set
  to "deny").

  The default value is `'ignore'`.

  - `'allow'` No special treatment for dotfiles.
  - `'deny'` Send a 403 for any request for a dotfile.
  - `'ignore'` Pretend like the dotfile does not exist and 404.

##### etag

  Enable or disable etag generation, defaults to true.

##### extensions

  If a given file doesn't exist, try appending one of the given extensions,
  in the given order. By default, this is disabled (set to `false`). An
  example value that will serve extension-less HTML files: `['html', 'htm']`.
  This is skipped if the requested file already has an extension.

##### index

  By default send supports "index.html" files, to disable this
  set `false` or to supply a new index pass a string or an array
  in preferred order.

##### lastModified

  Enable or disable `Last-Modified` header, defaults to true. Uses the file
  system's last modified value.

##### maxAge

  Provide a max-age in milliseconds for http caching, defaults to 0.
  This can also be a string accepted by the
  [ms](https://www.npmjs.org/package/ms#readme) module.

##### root

  Serve files relative to `path`.

### Events

The `SendStream` is an event emitter and will emit the following events:

  - `error` an error occurred `(err)`
  - `directory` a directory was requested
  - `file` a file was requested `(path, stat)`
  - `headers` the headers are about to be set on a file `(res, path, stat)`
  - `stream` file streaming has started `(stream)`
  - `end` streaming has completed

### .pipe

The `pipe` method is used to pipe the response into the Node.js HTTP response
object, typically `send(req, path, options).pipe(res)`.

## Error-handling

  By default when no `error` listeners are present an automatic response will be made, otherwise you have full control over the response, aka you may show a 5xx page etc.

## Caching

  It does _not_ perform internal caching, you should use a reverse proxy cache such
  as Varnish for this, or those fancy things called CDNs. If your application is small enough that it would benefit from single-node memory caching, it's small enough that it does not need caching at all ;).

## Debugging

 To enable `debug()` instrumentation output export __DEBUG__:

```
$ DEBUG=send node app
```

## Running tests

```
$ npm install
$ npm test
```

## Examples

  Small:

```js
var http = require('http');
var send = require('send');

var app = http.createServer(function(req, res){
  send(req, req.url).pipe(res);
}).listen(3000);
```

  Serving from a root directory with custom error-handling:

```js
var http = require('http');
var send = require('send');
var url = require('url');

var app = http.createServer(function(req, res){
  // your custom error-handling logic:
  function error(err) {
    res.statusCode = err.status || 500;
    res.end(err.message);
  }

  // your custom headers
  function headers(res, path, stat) {
    // serve all files for download
    res.setHeader('Content-Disposition', 'attachment');
  }

  // your custom directory handling logic:
  function redirect() {
    res.statusCode = 301;
    res.setHeader('Location', req.url + '/');
    res.end('Redirecting to ' + req.url + '/');
  }

  // transfer arbitrary files from within
  // /www/example.com/public/*
  send(req, url.parse(req.url).pathname, {root: '/www/example.com/public'})
  .on('error', error)
  .on('directory', redirect)
  .on('headers', headers)
  .pipe(res);
}).listen(3000);
```

## License 

[MIT](LICENSE)

[npm-image]: https://img.shields.io/npm/v/send.svg?style=flat
[npm-url]: https://npmjs.org/package/send
[travis-image]: https://img.shields.io/travis/tj/send.svg?style=flat
[travis-url]: https://travis-ci.org/tj/send
[coveralls-image]: https://img.shields.io/coveralls/tj/send.svg?style=flat
[coveralls-url]: https://coveralls.io/r/tj/send?branch=master
[downloads-image]: https://img.shields.io/npm/dm/send.svg?style=flat
[downloads-url]: https://npmjs.org/package/send
[gittip-image]: https://img.shields.io/gittip/dougwilson.svg?style=flat
[gittip-url]: https://www.gittip.com/dougwilson/
