# vary

[![NPM Version](http://img.shields.io/npm/v/vary.svg?style=flat)](https://www.npmjs.org/package/vary)
[![Node.js Version](http://img.shields.io/badge/node.js->=_0.8-blue.svg?style=flat)](http://nodejs.org/download/)
[![Build Status](http://img.shields.io/travis/jshttp/vary.svg?style=flat)](https://travis-ci.org/jshttp/vary)
[![Coverage Status](https://img.shields.io/coveralls/jshttp/vary.svg?style=flat)](https://coveralls.io/r/jshttp/vary)
[![Gittip](http://img.shields.io/gittip/dougwilson.svg?style=flat)](https://www.gittip.com/dougwilson/)

Manipulate the HTTP Vary header

## Install

```sh
$ npm install vary
```

## API

```js
var vary = require('vary')
```

### vary(res, field)

Adds the given header `field` to the `Vary` response header of `res`.
This can be a string of a single field, a string of a valid `Vary`
header, or an array of multiple fields.

This will append the header if not already listed, otherwise leaves
it listed in the current location.

```js
// Append "Origin" to the Vary header of the response
vary(res, 'Origin')
```

### vary.append(header, field)

Adds the given header `field` to the `Vary` response header string `header`.
This can be a string of a single field, a string of a valid `Vary` header,
or an array of multiple fields.

This will append the header if not already listed, otherwise leaves
it listed in the current location. The new header string is returned.

```js
// Get header string appending "Origin" to "Accept, User-Agent"
vary.append('Accept, User-Agent', 'Origin')
```

## Testing

```sh
$ npm test
```

## License

[MIT](LICENSE)
