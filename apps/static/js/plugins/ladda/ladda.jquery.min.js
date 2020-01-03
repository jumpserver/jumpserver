/*!
 * Ladda for jQuery
 * http://lab.hakim.se/ladda
 * MIT licensed
 *
 * Copyright (C) 2015 Hakim El Hattab, http://hakim.se
 */
!function(a,b){if(void 0===b)return console.error("jQuery required for Ladda.jQuery");var c=[];b=b.extend(b,{ladda:function(b){"stopAll"===b&&a.stopAll()}}),b.fn=b.extend(b.fn,{ladda:function(d){var e=c.slice.call(arguments,1);return"bind"===d?(e.unshift(b(this).selector),a.bind.apply(a,e)):b(this).each(function(){var c,f=b(this);void 0===d?f.data("ladda",a.create(this)):(c=f.data("ladda"),c[d].apply(c,e))}),this}})}(this.Ladda,this.jQuery);