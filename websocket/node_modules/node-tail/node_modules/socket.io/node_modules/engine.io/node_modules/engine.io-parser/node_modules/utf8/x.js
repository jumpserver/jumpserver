var utf8 = require('./utf8.js');
var stringEscape = require('string-escape');

utf8.encode('\xA9');
// console.log(
// 	utf8.encode('\uD800\uDC01'),
// 	'\xF0\x90\x80\x81',
// 	utf8.encode('\uD800\uDC01') == '\xF0\x90\x80\x81'
// );

var obj = {
	'description': 'Low surrogate followed by another low surrogate',
	// 'decoded': '\uDC00\uDC00',
	// 'encoded': '\xED\xB0\x80\xED\xB0\x80'
	'decoded': '\xA9',
	'encoded': '\xED\xB0\x80'
};

// Encoding
actual = utf8.encode(obj.decoded);
expected = obj.encoded;

if (actual != expected) {
	console.log(
		'fail\n',
		'actual  ', stringEscape(actual), '\n',
		'expected', stringEscape(expected)
	);
} else {
	console.log('encoding successsssss')
}


// // Decoding
// actual = utf8.decode(obj.encoded);
// expected = obj.decoded;

// if (actual != expected) {
// 	console.log(
// 		'fail\n',
// 		'actual  ', actual, '\n',
// 		'expected', expected
// 	);
// } else {
// 	console.log('decoding successsssss')
// }