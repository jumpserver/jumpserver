# serve-static

[![NPM Version][npm-image]][npm-url]
[![NPM Downloads][downloads-image]][downloads-url]
[![Build Status][travis-image]][travis-url]
[![Test Coverage][coveralls-image]][coveralls-url]
[![Gratipay][gratipay-image]][gratipay-url]

## Install

```sh
$ npm install serve-static
```

## API

```js
var serveStatic = require('serve-static')
```

### serveStatic(root, options)

Create a new middleware function to serve files from within a given root
directory. The file to serve will be determined by combining `req.url`
with the provided root directory. When a file is not found, instead of
sending a 404 response, this module will instead call `next()` to move on
to the next middleware, allowing for stacking and fall-backs.

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
  - `'ignore'` Pretend like the dotfile does not exist and call `next()`.

##### etag

Enable or disable etag generation, defaults to true.

##### extensions

Set file extension fallbacks. When set, if a file is not found, the given
extensions will be added to the file name and search for. The first that
exists will be served. Example: `['html', 'htm']`.

The default value is `false`.

##### index

By default this module will send "index.html" files in response to a request
on a directory. To disable this set `false` or to supply a new index pass a
string or an array in preferred order.

##### lastModified

Enable or disable `Last-Modified` header, defaults to true. Uses the file
system's last modified value.

##### maxAge

Provide a max-age in milliseconds for http caching, defaults to 0. This
can also be a string accepted by the [ms](https://www.npmjs.org/package/ms#readme)
module.

##### redirect

Redirect to trailing "/" when the pathname is a dir. Defaults to `true`.

##### setHeaders

Function to set custom headers on response. Alterations to the headers need to
occur synchronously. The function is called as `fn(res, path, stat)`, where
the arguments are:

  - `res` the response object
  - `path` the file path that is being sent
  - `stat` the stat object of the file that is being sent

## Examples

### Serve files with vanilla node.js http server

```js
var finalhandler = require('finalhandler')
var http = require('http')
var serveStatic = require('serve-static')

// Serve up public/ftp folder
var serve = serveStatic('public/ftp', {'index': ['index.html', 'index.htm']})

// Create server
var server = http.createServer(function(req, res){
  var done = finalhandler(req, res)
  serve(req, res, done)
})

// Listen
server.listen(3000)
```

### Serve all files as downloads

```js
var contentDisposition = require('content-disposition')
var finalhandler = require('finalhandler')
var http = require('http')
var serveStatic = require('serve-static')

// Serve up public/ftp folder
var serve = serveStatic('public/ftp', {
  'index': false,
  'setHeaders': setHeaders
})

// Set header to force download
function setHeaders(res, path) {
  res.setHeader('Content-Disposition', contentDisposition(path))
}

// Create server
var server = http.createServer(function(req, res){
  var done = finalhandler(req, res)
  serve(req, res, done)
})

// Listen
server.listen(3000)
```

### Serving using express

```js
var connect = require('connect')
var serveStatic = require('serve-static')

var app = connect()

app.use(serveStatic('public/ftp', {'index': ['default.html', 'default.htm']}))
app.listen(3000)
```

## License

[MIT](LICENSE)

[npm-image]: https://img.shields.io/npm/v/serve-static.svg?style=flat
[npm-url]: https://npmjs.org/package/serve-static
[travis-image]: https://img.shields.io/travis/expressjs/serve-static.svg?style=flat
[travis-url]: https://travis-ci.org/expressjs/serve-static
[coveralls-image]: https://img.shields.io/coveralls/expressjs/serve-static.svg?style=flat
[coveralls-url]: https://coveralls.io/r/expressjs/serve-static
[downloads-image]: https://img.shields.io/npm/dm/serve-static.svg?style=flat
[downloads-url]: https://npmjs.org/package/serve-static
[gratipay-image]: https://img.shields.io/gratipay/dougwilson.svg?style=flat
[gratipay-url]: https://gratipay.com/dougwilson/
