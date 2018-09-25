(function(factory) {
	if (typeof define === 'function' && define.amd) {
		define(factory);
	} else if (typeof exports !== 'undefined') {
		module.exports = factory();
	} else {
		factory();
	}
}(this, function() {
	return void 0;
}));
