# etag

[![NPM Version][npm-image]][npm-url]
[![NPM Downloads][downloads-image]][downloads-url]
[![Node.js Version][node-version-image]][node-version-url]
[![Build Status][travis-image]][travis-url]
[![Test Coverage][coveralls-image]][coveralls-url]

Create simple ETags

## Installation

```sh
$ npm install etag
```

## API

```js
var etag = require('etag')
```

### etag(entity, [options])

Generate a strong ETag for the given entity. This should be the complete
body of the entity. Strings, `Buffer`s, and `fs.Stats` are accepted. By
default, a strong ETag is generated except for `fs.Stats`, which will
generate a weak ETag (this can be overwritten by `options.weak`).

```js
res.setHeader('ETag', etag(body))
```

#### Options

`etag` accepts these properties in the options object.

##### weak

Specifies if a "strong" or a "weak" ETag will be generated. The ETag can only
really be a strong as the given input.

## Testing

```sh
$ npm test
```

## Benchmark

```bash
$ npm run-script bench

> etag@1.5.1 bench nodejs-etag
> node benchmark/index.js

> node benchmark/body0-100b.js

  100B body

  1 test completed.
  2 tests completed.
  3 tests completed.
  4 tests completed.

  buffer - strong x   425,007 ops/sec ±1.47% (184 runs sampled)
* buffer - weak   x 1,009,859 ops/sec ±0.18% (197 runs sampled)
  string - strong x   442,096 ops/sec ±1.20% (181 runs sampled)
  string - weak   x   325,063 ops/sec ±0.31% (192 runs sampled)

> node benchmark/body1-1kb.js

  1KB body

  1 test completed.
  2 tests completed.
  3 tests completed.
  4 tests completed.

  buffer - strong x 263,069 ops/sec ±1.60% (190 runs sampled)
* buffer - weak   x 295,732 ops/sec ±0.43% (199 runs sampled)
  string - strong x 274,822 ops/sec ±1.15% (191 runs sampled)
  string - weak   x 169,473 ops/sec ±1.59% (194 runs sampled)

> node benchmark/body2-5kb.js

  5KB body

  1 test completed.
  2 tests completed.
  3 tests completed.
  4 tests completed.

  buffer - strong x 104,299 ops/sec ±0.60% (193 runs sampled)
* buffer - weak   x 108,126 ops/sec ±0.65% (196 runs sampled)
  string - strong x 101,736 ops/sec ±0.78% (194 runs sampled)
  string - weak   x 101,266 ops/sec ±0.85% (192 runs sampled)

> node benchmark/body3-10kb.js

  10KB body

  1 test completed.
  2 tests completed.
  3 tests completed.
  4 tests completed.

  buffer - strong x 59,007 ops/sec ±0.29% (198 runs sampled)
* buffer - weak   x 60,968 ops/sec ±0.48% (197 runs sampled)
  string - strong x 51,873 ops/sec ±1.78% (178 runs sampled)
  string - weak   x 52,307 ops/sec ±2.63% (193 runs sampled)

> node benchmark/body4-100kb.js

  100KB body

  1 test completed.
  2 tests completed.
  3 tests completed.
  4 tests completed.

  buffer - strong x 6,712 ops/sec ±0.11% (198 runs sampled)
* buffer - weak   x 6,716 ops/sec ±0.50% (196 runs sampled)
  string - strong x 6,397 ops/sec ±0.36% (196 runs sampled)
  string - weak   x 6,635 ops/sec ±0.15% (198 runs sampled)
```

## License

[MIT](LICENSE)

[npm-image]: https://img.shields.io/npm/v/etag.svg?style=flat
[npm-url]: https://npmjs.org/package/etag
[node-version-image]: https://img.shields.io/node/v/etag.svg?style=flat
[node-version-url]: http://nodejs.org/download/
[travis-image]: https://img.shields.io/travis/jshttp/etag.svg?style=flat
[travis-url]: https://travis-ci.org/jshttp/etag
[coveralls-image]: https://img.shields.io/coveralls/jshttp/etag.svg?style=flat
[coveralls-url]: https://coveralls.io/r/jshttp/etag?branch=master
[downloads-image]: https://img.shields.io/npm/dm/etag.svg?style=flat
[downloads-url]: https://npmjs.org/package/etag
