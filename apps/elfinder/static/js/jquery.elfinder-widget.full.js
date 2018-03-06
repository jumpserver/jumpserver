/* 
 * A jquery plugin to support the the yawd-elfinder widget
 * Author: yawd, http://www.yawd.eu
 * Version: 1.0
 * 
 * elfinder client configuration options can be found here:
 * https://github.com/Studio-42/elFinder/wiki/Client-configuration-options
 */

(function($) {
	
	var defaults = {
		file : {
			hash : '',
			name : '',
			path : '',
			url : '',
			size : '',
			mime : '',
			ts : '',
			dim : '',
			tmb : '',
			rootUrl : '',
			error : '',
			separator : '/',
		},
		keywords : {
			size : 'Size',
			path : 'Path',
			link : 'Link',
			modified : 'Modified',
			dimensions : 'Dimensions',
			update : 'Update',
			set : 'Set',
			clear : 'Clear'
		},
		elfinder : {
			url : '',
			height: '550px',
			sortType : 'date',
			sortOrder : 'desc',
			sortStickFolders : false,
			ui : ['toolbar', 'places', 'tree', 'path', 'stat'],
			commandsOptions : {
				quicklook : {
					googleDocsMimes : ['application/pdf', 'image/tiff', 'application/vnd.ms-office', 'application/msword', 'application/vnd.ms-word', 'application/vnd.ms-excel', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']
				}
			},
		}
	};

	$.fn.elfinderwidget = function(options) {
		return this.each(function() {
			//initialize plugin
			if (!$.data(this, 'plugin_elfinderwidget')) {
				$.data(this, 'plugin_elfinderwidget',
					new ElfinderWidget( this, options ));
            }
		});
	}

	/*
	 * Initialize the class members and call the init method
	 */
	function ElfinderWidget(element, options) {

		this.el = $(element);
		this.id = this.el.attr('id').replace(/-widget$/,'');
		
		var elw = this;
		this.options = { 
			file : $.extend({}, defaults.file, options.file),
			elfinder : $.extend({}, defaults.elfinder, options.elfinder, {
				getFileCallback : function(file) {
					//generate file preview
					elw.preview(file);
					//update input fields
					elw.updateFile(file);
					//update buttons
					elw.updateButtons();
					//hide elfinder & elfinder wrapper
					elw.elfinder.parent().hide();
					elw.elfinder.elfinder('hide');
					return;
				}
			}),
			keywords : $.extend({}, defaults.keywords, options.keywords) 
		};
		this.init();
	}
	
	/*
	 * Create the html structure and wrap the hidden input
	 */
	ElfinderWidget.prototype.init = function() {
		
		this.el.wrap('<div class="elfinder-widget"/>')
		
		//Initialize elfinder		
		this.elfinder = $('<div id="' + this.id + '-elfinder" class="elfinder-root" />')
			.appendTo(
				$('<div class="elfinder-wrapper" />')
				.insertAfter(this.el.parent())
			).elfinder(this.options.elfinder);

		//Initialize preview
		this.pr = $('<div class="preview" />').insertAfter(this.el);
		this.options.file.error
			? this.pr.append(this.options.file.error)
			: this.preview(this.options.file);

		this.buttons();
		
		//initialize close
		var elf = this.elfinder;
		$('<div class="elfinder-close" /><div class="clear"></div>')
			.click(function() {
				elf.parent().hide();
				elf.elfinder('hide');
			}).insertBefore(this.elfinder);

		this.elfinder.elfinder('instance').destroy();
	}
	
	/*
	 * Generate the preview div based on a dictionary of attributes
	 */
	ElfinderWidget.prototype.preview = function(file) {
		
		if (!file.name) return;

		var header = $('<div class="elfinder-info-title"><span class="elfinder-cwd-icon"/></div>')
			.append('<strong>'+file.name+'</strong><span class="elfinder-info-kind">'+file.mime.split('/').reverse().join(" ").capitalize()+'</span>')

		file.tmb
			? $('.elfinder-cwd-icon', header).addClass('tmb').css('background-image', 'url(' + file.tmb + ')')
			: $('.elfinder-cwd-icon', header).addClass('elfinder-cwd-icon-' + file.mime.split('/').join(' elfinder-cwd-icon-'));
		
		var fileurl = file.pathUrl
				? file.pathUrl
				: file.url.replace(/\/$/,'') + '/' + file.path.split(file.separator).slice(1).join('/');

		var table = $('<table class="elfinder-info-tb"><tbody/></table>')
			.append('<tr><td>' + this.options.keywords.size + ':</td><td>' + elFinder.prototype.formatSize(file.size) + '</td></tr>')
			.append('<tr><td>' + this.options.keywords.path + ':</td><td>' + file.path + '</td></tr>')
			.append('<tr><td>' + this.options.keywords.link + ':</td><td><a href="' + fileurl + '" target="_blank">' + file.name + '</a></td></tr>')
			.append('<tr><td>' + this.options.keywords.modified + ':</td><td>' + this.elfinder.elfinder('instance').formatDate(file) + '</td></tr>');

		if (file.dim) table.append('<tr><td>' + this.options.keywords.dimensions + ':</td><td>' + file.dim + '</td></tr>');
			
		this.pr.empty().append(header, table);
	}
	
	/*
	 * Initialize the widget's set/update and clear buttons
	 */
	ElfinderWidget.prototype.buttons = function () {
		
		var elf = this.elfinder;
		var opts = this.options;
		var pr = this.pr;
		var el = this.el;
		var setkey = this.options.keywords.set;
	
		var set = $('<button class="button btn btn-info default" />')
			.click(function() {
				elf.parent().show();
				elf.elfinder(opts.elfinder).elfinder('show');
				return false;
			}).text(this.options.file.hash ? this.options.keywords.update : this.options.keywords.set);
		
		this.set = set;
		
		this.clear = $('<button class="button btn btn-danger default" />')
			.click(function() {
				pr.empty();
				el.val('');
				set.text(setkey);
				$(this).attr('disabled','disabled');
				return false;
			}).text(this.options.keywords.clear);
		
		if (!this.options.file.hash)
			this.clear.attr('disabled','disabled');

		$('<div/>').append(this.set, this.clear).insertAfter(this.pr);
		this.set.after('&#xa0;');
		
	};
	
	ElfinderWidget.prototype.updateButtons = function() {
		this.set.text(this.options.keywords.update);
		this.clear.removeAttr('disabled');
	};
	
	ElfinderWidget.prototype.updateFile = function(file) {
		this.el.val(file.hash);
		$.extend(this.options.file, file);
	};
	
	String.prototype.capitalize = function() {
	    return this.charAt(0).toUpperCase() + this.slice(1);
	};
	
	// Activate elfinder widget on dynamically added row in inlines in admin.
	// Thanks to etienne for the workaround, original code at:
	// https://bitbucket.org/etienned/django-autocomplete/commits/0ec7260445d8/
	$(window).load(function() {
		// Get all the inlines
	    $('.inline-group').each(function() {
	        var inlineGroup = $(this);
	        var elWidgets = [];
	        // For each inlines check for elfinder input in the empty form
	        inlineGroup.find('.empty-form .elfinder-widget').each(function() {
	            var el = $(this);
	            // Copy the script tag and restore the pre-elfinder state
	            var script = el.nextAll('script');
	            elWidgets.push(script);
	            elfinder = el.find('input');
	            el.before($('<input id="' + elfinder.attr('id') + '" size="' + elfinder.attr('size') + '" type="hidden" />'));	           
	            el.nextAll().remove();
	            el.remove();
	        });
	        if (elWidgets.length > 0) {
	            inlineGroup.find('.add-row a').attr('href', '#').click(function() {
	                // Find the current id #
	                var num = $('#id_' + inlineGroup.attr('id').replace(/group$/, 'TOTAL_FORMS')).val() - 1;
	                $.each(elWidgets, function() {
	                    // Clone the script tag, add the id # and append the tag
	                    var widget = $(this).clone();	                   
	                    widget.text(widget.text().replace('__prefix__', num));
	                    inlineGroup.append(widget);
	                });
	            });
	        }
	    });
	});

})(jQuery);

var yawdelfinder = {};
yawdelfinder.jQuery = jQuery.noConflict(true);
