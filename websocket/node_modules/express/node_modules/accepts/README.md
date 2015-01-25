# accepts

[![NPM Version][npm-image]][npm-url]
[![NPM Downloads][downloads-image]][downloads-url]
[![Node.js Version][node-version-image]][node-version-url]
[![Build Status][travis-image]][travis-url]
[![Test Coverage][coveralls-image]][coveralls-url]

Higher level content negotation based on [negotiator](https://github.com/federomero/negotiator). Extracted from [koa](https://github.com/koajs/koa) for general use.

In addition to negotatior, it allows:

- Allows types as an array or arguments list, ie `(['text/html', 'application/json'])` as well as `('text/html', 'application/json')`.
- Allows type shorthands such as `json`.
- Returns `false` when no types match
- Treats non-existent headers as `*`

## API

### var accept = new Accepts(req)

```js
var accepts = require('accepts')

http.createServer(function (req, res) {
  var accept = accepts(req)
})
```

### accept\[property\]\(\)

Returns all the explicitly accepted content property as an array in descending priority.

- `accept.types()`
- `accept.encodings()`
- `accept.charsets()`
- `accept.languages()`

They are also aliased in singular form such as `accept.type()`. `accept.languages()` is also aliased as `accept.langs()`, etc.

Note: you should almost never do this in a real app as it defeats the purpose of content negotiation.

Example:

```js
// in Google Chrome
var encodings = accept.encodings() // -> ['sdch', 'gzip', 'deflate']
```

Since you probably don't support `sdch`, you should just supply the encodings you support:

```js
var encoding = accept.encodings('gzip', 'deflate') // -> 'gzip', probably
```

### accept\[property\]\(values, ...\)

You can either have `values` be an array or have an argument list of values.

If the client does not accept any `values`, `false` will be returned.
If the client accepts any `values`, the preferred `value` will be return.

For `accept.types()`, shorthand mime types are allowed.

Example:

```js
// req.headers.accept = 'application/json'

accept.types('json') // -> 'json'
accept.types('html', 'json') // -> 'json'
accept.types('html') // -> false

// req.headers.accept = ''
// which is equivalent to `*`

accept.types() // -> [], no explicit types
accept.types('text/html', 'text/json') // -> 'text/html', since it was first
```

## License

[MIT](LICENSE)

[npm-image]: https://img.shields.io/npm/v/accepts.svg?style=flat
[npm-url]: https://npmjs.org/package/accepts
[node-version-image]: https://img.shields.io/node/v/accepts.svg?style=flat
[node-version-url]: http://nodejs.org/download/
[travis-image]: https://img.shields.io/travis/jshttp/accepts.svg?style=flat
[travis-url]: https://travis-ci.org/jshttp/accepts
[coveralls-image]: https://img.shields.io/coveralls/jshttp/accepts.svg?style=flat
[coveralls-url]: https://coveralls.io/r/jshttp/accepts
[downloads-image]: https://img.shields.io/npm/dm/accepts.svg?style=flat
[downloads-url]: https://npmjs.org/package/accepts
