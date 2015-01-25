/*!
 * vary
 * Copyright(c) 2014 Douglas Christopher Wilson
 * MIT Licensed
 */

/**
 * Module exports.
 */

module.exports = vary;
module.exports.append = append;

/**
 * Variables.
 */

var separators = /[\(\)<>@,;:\\"\/\[\]\?=\{\}\u0020\u0009]/;

/**
 * Append a field to a vary header.
 *
 * @param {String} header
 * @param {String|Array} field
 * @return {String}
 * @api public
 */

function append(header, field) {
  if (typeof header !== 'string') {
    throw new TypeError('header argument is required');
  }

  if (!field) {
    throw new TypeError('field argument is required');
  }

  // get fields array
  var fields = !Array.isArray(field)
    ? parse(String(field))
    : field;

  // assert on invalid fields
  for (var i = 0; i < fields.length; i++) {
    if (separators.test(fields[i])) {
      throw new TypeError('field argument contains an invalid header');
    }
  }

  // existing, unspecified vary
  if (header === '*') {
    return header;
  }

  // enumerate current values
  var vals = parse(header.toLowerCase());

  // unspecified vary
  if (fields.indexOf('*') !== -1 || vals.indexOf('*') !== -1) {
    return '*';
  }

  for (var i = 0; i < fields.length; i++) {
    field = fields[i].toLowerCase();

    // append value (case-preserving)
    if (vals.indexOf(field) === -1) {
      vals.push(field);
      header = header
        ? header + ', ' + fields[i]
        : fields[i];
    }
  }

  return header;
}

/**
 * Parse a vary header into an array.
 *
 * @param {String} header
 * @return {Array}
 * @api private
 */

function parse(header) {
  return header.trim().split(/ *, */);
}

/**
 * Mark that a request is varied on a header field.
 *
 * @param {Object} res
 * @param {String|Array} field
 * @api public
 */

function vary(res, field) {
  if (!res || !res.getHeader || !res.setHeader) {
    // quack quack
    throw new TypeError('res argument is required');
  }

  // get existing header
  var val = res.getHeader('Vary') || ''
  var header = Array.isArray(val)
    ? val.join(', ')
    : String(val);

  // set new header
  res.setHeader('Vary', append(header, field));
}
