(function(root, factory) {
	if (typeof define === 'function' && define.amd) {
		define(['elfinder'], factory);
	} else if (typeof exports !== 'undefined') {
		module.exports = factory(require('elfinder'));
	} else {
		factory(root.elFinder);
	}
}(this, function(elFinder) {
"use strict";
try {
	if (! elFinder.prototype.commands.quicklook.plugins) {
		elFinder.prototype.commands.quicklook.plugins = [];
	}
	elFinder.prototype.commands.quicklook.plugins.push(function(ql) {
		var fm      = ql.fm,
			preview = ql.preview;
			
		preview.on('update', function(e) {
			var win  = ql.window,
				file = e.file, node, loading;
			
			if (file.mime.indexOf('application/vnd.google-apps.') === 0) {
				if (file.url == '1') {
					preview.hide();
					$('<div class="elfinder-quicklook-info-data"><button class="elfinder-info-button">'+fm.i18n('getLink')+'</button></div>').appendTo(ql.info.find('.elfinder-quicklook-info'))
					.on('click', function() {
						$(this).html('<span class="elfinder-info-spinner">');
						fm.request({
							data : {cmd : 'url', target : file.hash},
							preventDefault : true
						})
						.always(function() {
							preview.show();
							$(this).html('');
						})
						.done(function(data) {
							var rfile = fm.file(file.hash);
							ql.value.url = rfile.url = data.url || '';
							if (ql.value.url) {
								preview.trigger($.Event('update', {file : ql.value}));
							}
						});
					});
				}
				if (file.url !== '' && file.url != '1') {
					e.stopImmediatePropagation();
					preview.one('change', function() {
						loading.remove();
						node.off('load').remove();
					});
					
					loading = $('<div class="elfinder-quicklook-info-data">'+fm.i18n('nowLoading')+'<span class="elfinder-info-spinner"></div>').appendTo(ql.info.find('.elfinder-quicklook-info'));
					
					node = $('<iframe class="elfinder-quicklook-preview-iframe"/>')
						.css('background-color', 'transparent')
						.appendTo(preview)
						.on('load', function() {
							ql.hideinfo();
							loading.remove();
							$(this).css('background-color', '#fff').show();
						})
						.attr('src', fm.url(file.hash));
				}
			}
			
		});
	});
} catch(e) {}
}));
