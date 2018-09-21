(function(editors, elFinder) {
	if (typeof define === 'function' && define.amd) {
		define(['elfinder'], editors);
	} else if (elFinder) {
		var optEditors = elFinder.prototype._options.commandsOptions.edit.editors;
		elFinder.prototype._options.commandsOptions.edit.editors = optEditors.concat(editors(elFinder));
	}
}(function(elFinder) {
	"use strict";
	var apps = {},
		// get query of getfile
		getfile = window.location.search.match(/getfile=([a-z]+)/),
		useRequire = elFinder.prototype.hasRequire,
		hasFlash = (function() {
			var hasFlash;
			try {
				hasFlash = !!(new ActiveXObject('ShockwaveFlash.ShockwaveFlash'));
			} catch (e) {
				hasFlash = !!(typeof window.orientation === 'undefined' || (navigator && navigator.mimeTypes["application/x-shockwave-flash"]));
			}
			return hasFlash;
		})(),
		ext2mime = {
			bmp: 'image/x-ms-bmp',
			dng: 'image/x-adobe-dng',
			gif: 'image/gif',
			jpeg: 'image/jpeg',
			jpg: 'image/jpeg',
			pdf: 'application/pdf',
			png: 'image/png',
			ppm: 'image/x-portable-pixmap',
			psd: 'image/vnd.adobe.photoshop',
			pxd: 'image/x-pixlr-data',
			svg: 'image/svg+xml',
			tiff: 'image/tiff',
			webp: 'image/webp',
			xcf: 'image/x-xcf',
			sketch: 'application/x-sketch'
		},
		mime2ext,
		getExtention = function(mime, fm) {
			if (!mime2ext) {
				mime2ext = fm.arrayFlip(ext2mime);
			}
			var ext = mime2ext[mime] || fm.mimeTypes[mime];
			if (ext === 'jpeg') {
				ext = 'jpg';
			}
			return ext;
		},
		initImgTag = function(id, file, content, fm) {
			var node = $(this).children('img:first').data('ext', getExtention(file.mime, fm)),
				spnr = $('<div/>')
					.css({
						position: 'absolute',
						top: '50%',
						textAlign: 'center',
						width: '100%',
						fontSize: '16pt'
					})
					.html(fm.i18n('ntfloadimg'))
					.hide()
					.appendTo(this);
			
			node.attr('id', id+'-img')
				.attr('src', content)
				.css({'height':'', 'max-width':'100%', 'max-height':'100%', 'cursor':'pointer'})
				.data('loading', function(done) {
					var btns = node.closest('.elfinder-dialog').find('button,.elfinder-titlebar-button');
					btns.prop('disabled', !done)[done? 'removeClass' : 'addClass']('ui-state-disabled');
					node.css('opacity', done? '' : '0.3');
					spnr[done? 'hide' : 'show']();
					return node;
				});
		},
		imgBase64 = function(node, mime) {
			var style = node.attr('style'),
				img, canvas, ctx, data;
			try {
				// reset css for getting image size
				node.attr('style', '');
				// img node
				img = node.get(0);
				// New Canvas
				canvas = document.createElement('canvas');
				canvas.width  = img.width;
				canvas.height = img.height;
				// restore css
				node.attr('style', style);
				// Draw Image
				canvas.getContext('2d').drawImage(img, 0, 0);
				// To Base64
				data = canvas.toDataURL(mime);
			} catch(e) {
				data = node.attr('src');
			}
			return data;
		},
		pixlrCallBack = function() {
			if (!hasFlash || window.parent === window) {
				return;
			}
			var pixlr = window.location.search.match(/[?&]pixlr=([^&]+)/),
				image = window.location.search.match(/[?&]image=([^&]+)/),
				p, ifm, url, node, ext;
			if (pixlr) {
				// case of redirected from pixlr.com
				p = window.parent;
				ifm = p.$('#'+pixlr[1]+'iframe').hide();
				node = p.$('#'+pixlr[1]).data('resizeoff')();
				if (image[1].substr(0, 4) === 'http') {
					url = image[1];
					ext = url.replace(/.+\.([^.]+)$/, '$1');
					if (node.data('ext') !== ext) {
						node.closest('.ui-dialog').trigger('changeType', {
							extention: ext,
							mime : ext2mime[ext]
						});
					}
					if (window.location.protocol === 'https:') {
						url = url.replace(/^http:/, 'https:');
					}
					node.on('load error', function() {
							node.data('loading')(true);
						})
						.attr('src', url)
						.data('loading')();
				} else {
					node.data('loading')(true);
				}
				ifm.trigger('destroy').remove();
			}
		},
		pixlrSetup = function(opts, fm) {
			if (!hasFlash || fm.UA.ltIE8) {
				this.disabled = true;
			}
		},
		pixlrLoad = function(mode, base) {
			var self = this,
				fm = this.fm,
				clPreventBack = fm.res('class', 'preventback'),
				node = $(base).children('img:first')
					.data('loading')()
					.data('resizeoff', function() {
						$(window).off('resize.'+node.attr('id'));
						dialog.addClass(clPreventBack);
						return node;
					})
					.on('click', function() {
						launch();
					}),
				dialog = $(base).closest('.ui-dialog'),
				elfNode = fm.getUI(),
				uiToast = fm.getUI('toast'),
				container = $('<iframe class="ui-front" allowtransparency="true">'),
				file = this.file,
				timeout = 15,
				error = function(error) {
					if (error) {
						container.trigger('destroy').remove();
						node.data('loading')(true);
						fm.error(error);
					} else {
						uiToast.appendTo(dialog.closest('.ui-dialog'));
						fm.toast({
							mode: 'info',
							msg: 'Can not launch Pixlr yet. Waiting ' + timeout + ' seconds.',
							button: {
								text: 'Abort',
								click: function() {
									container.trigger('destroy').remove();
									node.data('loading')(true);
								}
							},
							onHidden: function() {
								uiToast.children().length === 1 && uiToast.appendTo(fm.getUI());
							}
						});
						errtm = setTimeout(error, timeout * 1000);
					}
				},
				launch = function() {
					var src = 'https://pixlr.com/'+mode+'/?s=c',
						myurl = window.location.href.toString().replace(/#.*$/, ''),
						opts = {};

					errtm = setTimeout(error, timeout * 1000);
					myurl += (myurl.indexOf('?') === -1? '?' : '&') + 'pixlr='+node.attr('id');
					src += '&referrer=elFinder&locktitle=true';
					src += '&exit='+encodeURIComponent(myurl+'&image=0');
					src += '&target='+encodeURIComponent(myurl);
					src += '&title='+encodeURIComponent(file.name);
					src += '&image='+encodeURIComponent(node.attr('src'));
					
					opts.src = src;
					opts.css = {
						width: '100%',
						height: $(window).height()+'px',
						position: 'fixed',
						display: 'block',
						backgroundColor: 'transparent',
						border: 'none',
						top: 0,
						right: 0
					};

					// trigger event 'editEditorPrepare'
					self.trigger('Prepare', {
						node: base,
						editorObj: void(0),
						instance: container,
						opts: opts
					});

					container
						.attr('id', node.attr('id')+'iframe')
						.attr('src', opts.src)
						.css(opts.css)
						.one('load', function() {
							errtm && clearTimeout(errtm);
							setTimeout(function() {
								if (container.is(':hidden')) {
									error('Please disable your ad blocker.');
								}
							}, 1000);
							dialog.addClass(clPreventBack);
							fm.toggleMaximize(container, true);
							fm.toFront(container);
						})
						.on('destroy', function() {
							fm.toggleMaximize(container, false);
						})
						.on('error', error)
						.appendTo(elfNode.hasClass('elfinder-fullscreen')? elfNode : 'body');
				},
				errtm;
			$(base).on('saveAsFail', launch);
			launch();
		},
		iframeClose = function(ifm) {
			var $ifm = $(ifm),
				dfd = $.Deferred().always(function() {
					$ifm.off('load', load);
				}),
				ab = 'about:blank',
				chk = function() {
					tm = setTimeout(function() {
						var src;
						try {
							src = base.contentWindow.location.href;
						} catch(e) {
							src = null;
						}
						if (src === ab) {
							dfd.resolve();
						} else if (--cnt > 0){
							chk();
						} else {
							dfd.reject();
						}
					}, 500);
				},
				load = function() {
					tm && clearTimeout(tm);
					dfd.resolve();
				},
				cnt = 20, // 500ms * 20 = 10sec wait
				tm;
			$ifm.one('load', load);
			ifm.src = ab;
			chk();
			return dfd;
		};
	
	// check callback from pixlr
	pixlrCallBack();
	
	// check getfile callback function
	if (getfile) {
		getfile = getfile[1];
		if (getfile === 'ckeditor') {
			elFinder.prototype._options.getFileCallback = function(file, fm) {
				window.opener.CKEDITOR.tools.callFunction((function() {
					var reParam = new RegExp('(?:[\?&]|&amp;)CKEditorFuncNum=([^&]+)', 'i'),
						match = window.location.search.match(reParam);
					return (match && match.length > 1) ? match[1] : '';
				})(), fm.convAbsUrl(file.url));
				fm.destroy();
				window.close();
			};
		} else if (getfile === 'tinymce') {
			elFinder.prototype._options.getFileCallback = function(file, fm) {
				// pass selected file data to TinyMCE
				parent.tinymce.activeEditor.windowManager.getParams().oninsert(file, fm);
				// close popup window
				parent.tinymce.activeEditor.windowManager.close();
			};
		}
	}
	
	// return editors Array
	return [
		{
			// tui.image-editor - https://github.com/nhnent/tui.image-editor
			info : {
				id: 'tuiimgedit',
				name: 'TUI Image Editor',
				iconImg: 'img/editor-icons.png 0 -48',
				dataScheme: true,
				schemeContent: true,
				openMaximized: true,
				canMakeEmpty: false,
				integrate: {
					title: 'TOAST UI Image Editor',
					link: 'http://ui.toast.com/tui-image-editor/'
				}
			},
			// MIME types to accept
			mimes : ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/x-ms-bmp'],
			// HTML of this editor
			html : '<div class="elfinder-edit-imageeditor"><canvas></canvas></div>',
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				if (fm.UA.ltIE8 || fm.UA.Mobile) {
					this.disabled = true;
				} else {
					this.opts = Object.assign({}, opts.extraOptions.tuiImgEditOpts || {}, {
						iconsPath : fm.baseUrl + 'img/tui-',
						theme : {}
					});
					if (!fm.isSameOrigin(this.opts.iconsPath)) {
						this.disabled = true;
						fm.debug('warning', 'Setting `commandOptions.edit.extraOptions.tuiImgEditOpts.iconsPath` MUST follow the same origin policy.');
					}
				}
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, content, fm) {
				this.data('url', content);
			},
			load : function(base) {
				var self = this,
					fm   = this.fm,
					dfrd = $.Deferred(),
					cdns = fm.options.cdns,
					ver  = 'latest',
					init = function(editor) {
						var $base = $(base),
							opts = self.confObj.opts,
							iconsPath = opts.iconsPath,
							iEditor = new editor(base, {
								includeUI: {
									loadImage: {
										path: $base.data('url'),
										name: self.file.name
									},
									theme: Object.assign(opts.theme, {
										// main icons
										'menu.normalIcon.path': iconsPath + 'icon-b.svg',
										'menu.normalIcon.name': 'icon-b',
										'menu.activeIcon.path': iconsPath + 'icon-a.svg',
										'menu.activeIcon.name': 'icon-a',
										// submenu icons
										'submenu.normalIcon.path': iconsPath + 'icon-a.svg',
										'submenu.normalIcon.name': 'icon-a',
										'submenu.activeIcon.path': iconsPath + 'icon-c.svg',
										'submenu.activeIcon.name': 'icon-c',
									}),
									initMenu: 'filter',
									menuBarPosition: 'bottom'
								},
								cssMaxWidth: 700,
								cssMaxHeight: 500
							}),
							canvas = $base.find('canvas:first').get(0),
							zoom = function(v) {
								var c = $(canvas),
									w = parseInt(c.attr('width')),
									h = parseInt(c.attr('height')),
									a = w / h,
									mw, mh, css;
								if (v === 0) {
									mw = w;
									mh = h;
								} else {
									mw = parseInt(c.css('max-width')) + Number(v);
									mh = mw / a;
								}
								css = {
									maxWidth: mw,
									maxHeight: mh
								};
								per.text(Math.round(mw / w * 100) + '%');
								if (typeof v !== 'undefined') {
									// set editor config directly for change scale
									iEditor._graphics.cssMaxWidth = mw;
									iEditor._graphics.cssMaxHeight = mh;
									// change scale
									c.css(css).next().css(css);
									c.parents('.tui-image-editor-canvas-container,tui-image-editor-canvas').css(css);
									c.closest('.tui-image-editor').css({
										width: mw,
										height: mh
									});
									// continually change more
									if (zoomMore) {
										setTimeout(function() {
											zoomMore && zoom(v);
										}, 50);
									}
								}
							},
							zup = $('<span class="ui-icon ui-icon-plusthick"/>').data('val', 10),
							zdown = $('<span class="ui-icon ui-icon-minusthick"/>').data('val', -10),
							per = $('<button/>').css('width', '4em').text('%').attr('title', '100%').data('val', 0),
							quty, qutyTm, zoomTm, zoomMore;

						$base.removeData('url').data('mime', self.file.mime);
						// jpeg quality controls
						if (self.file.mime === 'image/jpeg') {
							$base.data('quality', fm.storage('jpgQuality') || fm.option('jpgQuality'));
							quty = $('<input type="number" class="ui-corner-all elfinder-resize-quality elfinder-tabstop"/>')
								.attr('min', '1')
								.attr('max', '100')
								.attr('title', '1 - 100')
								.on('change', function() {
									var q = quty.val();
									$base.data('quality', q);
									qutyTm && cancelAnimationFrame(qutyTm);
									qutyTm = requestAnimationFrame(function() {
										canvas.toBlob(function(blob) {
											blob && quty.next('span').text(' (' + fm.formatSize(blob.size) + ')');
										}, 'image/jpeg', Math.max(Math.min(q, 100), 1) / 100);
									});
								})
								.val($base.data('quality'));
							$('<div class="ui-dialog-buttonset elfinder-edit-extras elfinder-edit-extras-quality"/>')
								.append(
									$('<span>').html(fm.i18n('quality') + ' : '), quty, $('<span/>')
								)
								.prependTo($base.parent().next());
						} else if (self.file.mime === 'image/svg+xml') {
							$base.closest('.ui-dialog').trigger('changeType', {
								extention: 'png',
								mime : 'image/png',
								keepEditor: true
							});
						}
						// zoom scale controls
						$('<div class="ui-dialog-buttonset elfinder-edit-extras"/>')
							.append(
								zdown, per, zup
							)
							.attr('title', fm.i18n('scale'))
							.on('click', 'span,button', function() {
								zoom($(this).data('val'));
							})
							.on('mousedown mouseup mouseleave', 'span', function(e) {
								zoomMore = false;
								zoomTm && clearTimeout(zoomTm);
								if (e.type === 'mousedown') {
									zoomTm = setTimeout(function() {
										zoomMore = true;
										zoom($(e.target).data('val'));
									}, 500);
								}
							})
							.prependTo($base.parent().next());

						// wait canvas ready
						setTimeout(function() {
							dfrd.resolve(iEditor);
							if (quty) {
								quty.trigger('change');
								iEditor.on('redoStackChanged undoStackChanged', function() {
									quty.trigger('change');
								});
							}
							// show initial scale
							zoom(null);
						}, 100);
					},
					loader;

				if (!self.confObj.editor) {
					loader = $.Deferred();
					fm.loadCss([
						cdns.tui + '/tui-color-picker/latest/tui-color-picker.css',
						cdns.tui + '/tui-image-editor/'+ver+'/tui-image-editor.css'
					]);
					if (fm.hasRequire) {
						require.config({
							paths : {
								'fabric/dist/fabric.require' : cdns.fabric16 + '/fabric.require.min',
								'tui-code-snippet' : cdns.tui + '/tui.code-snippet/latest/tui-code-snippet.min',
								'tui-color-picker' : cdns.tui + '/tui.code-snippet/latest/tui-color-picker.min',
								'tui-image-editor' : cdns.tui + '/tui-image-editor/'+ver+'/tui-image-editor.min'
							}
						});
						require(['tui-image-editor'], function(ImageEditor) {
							loader.resolve(ImageEditor);
						});
					} else {
						fm.loadScript([
							cdns.fabric16 + '/fabric.min.js',
							cdns.tui + '/tui.code-snippet/latest/tui-code-snippet.min.js'
						], function() {
							fm.loadScript([
								cdns.tui + '/tui-color-picker/latest/tui-color-picker.min.js'
							], function() {
								fm.loadScript([
									cdns.tui + '/tui-image-editor/'+ver+'/tui-image-editor.min.js'
								], function() {
									loader.resolve(window.tui.ImageEditor);
								}, {
									loadType: 'tag'
								});
							}, {
								loadType: 'tag'
							});
						}, {
							loadType: 'tag'
						});
					}
					loader.done(function(editor) {
						self.confObj.editor = editor;
						init(editor);
					});
				} else {
					init(self.confObj.editor);
				}
				return dfrd;
			},
			getContent : function(base) {
				var editor = this.editor,
					fm = editor.fm,
					$base = $(base),
					quality = $base.data('quality');
				if (editor.instance) {
					if ($base.data('mime') === 'image/jpeg') {
						quality = quality || fm.storage('jpgQuality') || fm.option('jpgQuality');
						quality = Math.max(0.1, Math.min(1, quality / 100));
					}
					return editor.instance.toDataURL({
						format: getExtention($base.data('mime'), fm),
						quality: quality
					});
				}
			},
			save : function(base) {
				var $base = $(base),
					quality = $base.data('quality'),
					hash = $base.data('hash'),
					file;
				this.instance.deactivateAll();
				if (typeof quality !== 'undefined') {
					this.fm.storage('jpgQuality', quality);
				}
				if (hash) {
					file = this.fm.file(hash);
					$base.data('mime', file.mime);
				}
			}
		},
		{
			// Pixlr Editor
			info : {
				id : 'pixlreditor',
				name : 'Pixlr Editor',
				iconImg : 'img/editor-icons.png 0 -128',
				urlAsContent: true,
				schemeContent: true,
				single: true,
				canMakeEmpty: true,
				integrate: {
					title: 'PIXLR EDITOR',
					link: 'https://pixlr.com/editor/'
				}
			},
			// MIME types to accept
			mimes : ['image/jpeg', 'image/png', 'image/gif', 'image/x-ms-bmp', 'image/x-pixlr-data'],
			// HTML of this editor
			html : '<div class="elfinder-edit-imageeditor"><img/></div>',
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				pixlrSetup.call(this, opts, fm);
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, url, fm) {
				initImgTag.call(this, id, file, file.size > 0? fm.convAbsUrl(url) : '', fm);
			},
			// Get data uri scheme (this: this editors HTML node)
			getContent : function() {
				return $(this).children('img:first').attr('src');
			},
			load : function(base) {
				pixlrLoad.call(this, 'editor', base);
			},
			save : function(base) {},
			close : function(base) {}
		},
		{
			// Pixlr Express
			info : {
				id: 'pixlrexpress',
				name : 'Pixlr Express',
				iconImg : 'img/editor-icons.png 0 -112',
				urlAsContent: true,
				schemeContent: true,
				single: true,
				canMakeEmpty: false,
				integrate: {
					title: 'PIXLR EXPRESS',
					link: 'https://pixlr.com/express/'
				}
			},
			// MIME types to accept
			mimes : ['image/jpeg', 'image/png', 'image/gif'],
			// HTML of this editor
			html : '<div class="elfinder-edit-imageeditor"><img/></div>',
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				pixlrSetup.call(this, opts, fm);
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, url, fm) {
				initImgTag.call(this, id, file, file.size > 0? fm.convAbsUrl(url) : '', fm);
			},
			// Get data uri scheme (this: this editors HTML node)
			getContent : function() {
				return $(this).children('img:first').attr('src');
			},
			load : function(base) {
				pixlrLoad.call(this, 'express', base);
			},
			save : function(base) {},
			close : function(base) {}
		},
		{
			// Photopea advanced image editor
			info : {
				id : 'photopea',
				name : 'Photopea',
				iconImg : 'img/editor-icons.png 0 -160',
				single: true,
				urlAsContent: true,
				arrayBufferContent: true,
				openMaximized: true,
				canMakeEmpty: true,
				integrate: {
					title: 'Photopea',
					link: 'https://www.photopea.com/learn/'
				}
			},
			mimes : ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/x-ms-bmp', 'image/tiff', 'image/x-adobe-dng', 'image/webp', 'image/x-xcf', 'image/vnd.adobe.photoshop', 'application/pdf', 'image/x-portable-pixmap', 'image/x-sketch'],
			html : '<iframe style="width:100%;height:100%;border:none;"></iframe>',
			// setup on elFinder bootup
			setup : function(opts, fm) {
				if (fm.UA.IE || fm.UA.Mobile) {
					this.disabled = true;
				}
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, dum, fm) {
				var orig = 'https://www.photopea.com',
					ifm = $(this).hide()
						//.css('box-sizing', 'border-box')
						.on('load', function() {
							//spnr.remove();
							ifm.show();
						})
						.on('error', function() {
							spnr.remove();
							ifm.show();
						}),
					editor = this.editor,
					confObj = editor.confObj,
					spnr = $('<div/>')
						.css({
							position: 'absolute',
							top: '50%',
							textAlign: 'center',
							width: '100%',
							fontSize: '16pt'
						})
						.html(fm.i18n('nowLoading') + '<span class="elfinder-spinner"/>')
						.appendTo(ifm.parent()),
					getType = function(mime) {
						var ext = getExtention(mime, fm),
							extmime = ext2mime[ext];

						if (!confObj.mimesFlip[extmime]) {
							ext = '';
						} else if (ext === 'jpeg') {
							ext = 'jpg';
						}
						if (!ext || ext === 'xcf' || ext === 'dng' || ext === 'sketch') {
							ext = 'psd';
							extmime = ext2mime[ext];
							ifm.closest('.ui-dialog').trigger('changeType', {
								extention: ext,
								mime : extmime,
								keepEditor: true
							});
						}
						return ext;
					},
					mime = file.mime,
					liveMsg, type;
				
				if (!confObj.mimesFlip) {
					confObj.mimesFlip = fm.arrayFlip(confObj.mimes, true);
				}
				if (!confObj.liveMsg) {
					confObj.liveMsg = function(ifm, spnr, file) {
						var url = fm.openUrl(file.hash);
							if (!fm.isSameOrigin(url)) {
								url = fm.openUrl(file.hash, true);
							}
						var wnd = ifm.get(0).contentWindow,
							phase = 0,
							data = null,
							dfdIni = $.Deferred().done(function() {
								spnr.remove();
								phase = 1;
								wnd.postMessage(data, '*');
							}),
							dfdGet;

						this.load = function() {
							return fm.request({
								data    : {cmd : 'get'},
								options : {
									url: url,
									type: 'get',
									cache : true,
									dataType : 'binary',
									responseType :'arraybuffer',
									processData: false
								}
							})
							.done(function(d) {
								data = d;
							});
						};

						this.receive = function(e) {
							var ev = e.originalEvent,
								state;
							if (ev.origin === orig && ev.source === wnd) {
								if (ev.data === 'done') {
									if (phase === 0) {
										dfdIni.resolve();
									} else if (phase === 1) {
										phase = 2;
										ifm.trigger('contentsloaded');
									} else {
										if (dfdGet && dfdGet.state() === 'pending') {
											dfdGet.reject('errDataEmpty');
										}
									}
								} else {
									if (dfdGet && dfdGet.state() === 'pending') {
										if (typeof ev.data === 'object') {
											dfdGet.resolve('data:' + mime + ';base64,' + fm.arrayBufferToBase64(ev.data));
										} else {
											dfdGet.reject('errDataEmpty');
										}
									}
								}
							}
						};

						this.getContent = function() {
							var type;
							if (phase > 1) {
								dfdGet && dfdGet.state() === 'pending' && dfdGet.reject();
								dfdGet = null;
								dfdGet = $.Deferred();
								if (phase === 2) {
									phase = 3;
									dfdGet.resolve('data:' + mime + ';base64,' + fm.arrayBufferToBase64(data));
									data = null;
									return dfdGet;
								}
								if (ifm.data('mime')) {
									mime = ifm.data('mime');
									type = getType(mime);
								}
								wnd.postMessage('app.activeDocument.saveToOE("' + type + '")', orig);
								return dfdGet;
							}
						};
					};
				}

				ifm.parent().css('padding', 0);
				type = getType(file.mime);
				liveMsg = editor.liveMsg = new confObj.liveMsg(ifm, spnr, file);
				$(window).on('message.' + fm.namespace, liveMsg.receive);
				liveMsg.load().done(function() {
					var d = JSON.stringify({
						files : [],
						environment : {
							lang: fm.lang.replace(/_/g, '-')
						}
					});
					ifm.attr('src', orig + '/#' + encodeURI(d));
				}).fail(function(err) {
					err && fm.error(err);
					editor.initFail = true;
				});
			},
			load : function(base) {
				var dfd = $.Deferred(),
					self = this,
					fm = this.fm,
					$base = $(base);
				if (self.initFail) {
					dfd.reject();
				} else {
					$base.on('contentsloaded', function() {
						dfd.resolve(self.liveMsg);
					});
				}
				return dfd;
			},
			getContent : function() {
				return this.editor.liveMsg? this.editor.liveMsg.getContent() : void(0);
			},
			save : function(base, liveMsg) {
				var $base = $(base),
					quality = $base.data('quality'),
					hash = $base.data('hash'),
					file;
				if (typeof quality !== 'undefined') {
					this.fm.storage('jpgQuality', quality);
				}
				if (hash) {
					file = this.fm.file(hash);
					$base.data('mime', file.mime);
				} else {
					$base.removeData('mime');
				}
			},
			// On dialog closed
			close : function(base, liveMsg) {
				$(base).attr('src', '');
				liveMsg && $(window).off('message.' + this.fm.namespace, liveMsg.receive);
			}
		},
		{
			// Adobe Creative SDK Creative Tools Image Editor UI
			// MIME types to accept
			info : {
				id : 'creativecloud',
				name : 'Creative Cloud',
				iconImg : 'img/editor-icons.png 0 -192',
				dataScheme: true,
				schemeContent: true,
				single: true,
				canMakeEmpty: false,
				integrate: {
					title: 'Adobe Creative Cloud',
					link: 'https://www.adobe.io/apis/creativecloud.html'
				}
			},
			mimes : ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/x-ms-bmp'],
			// HTML of this editor
			html : '<div class="elfinder-edit-imageeditor"><img/></div>',
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				if (fm.UA.ltIE8 || !opts.extraOptions || !opts.extraOptions.creativeCloudApiKey) {
					this.disabled = true;
				} else {
					this.apiKey = opts.extraOptions.creativeCloudApiKey;
				}
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, content, fm) {
				initImgTag.call(this, id, file, content, fm);
			},
			// Get data uri scheme (this: this editors HTML node)
			getContent : function() {
				return $(this).children('img:first').attr('src');
			},
			// Launch Aviary Feather editor when dialog open
			load : function(base) {
				var self = this,
					fm = this.fm,
					node = $(base).children('img:first'),
					dialog = $(base).closest('.ui-dialog'),
					elfNode = fm.getUI(),
					dfrd = $.Deferred(),
					container = $('#elfinder-aviary-container'),
					init = function(onload) {
						var getLang = function() {
								var langMap = {
									'zh_TW' : 'zh_HANT',
									'zh_CN' : 'zh_HANS'
								};
								return langMap[fm.lang]? langMap[fm.lang] : fm.lang;
							}, opts;
							
						if (!container.length) {
							container = $('<div id="elfinder-aviary-container" class="ui-front"/>').css({
								position: 'fixed',
								top: 0,
								right: 0,
								width: '100%',
								height: $(window).height(),
								overflow: 'auto'
							}).hide().appendTo(elfNode.hasClass('elfinder-fullscreen')? elfNode : 'body');
							// bind switch fullscreen event
							elfNode.on('resize.'+fm.namespace, function(e, data) {
								e.preventDefault();
								e.stopPropagation();
								data && data.fullscreen && container.appendTo(data.fullscreen === 'on'? elfNode : 'body');
							});
							fm.bind('destroy', function() {
								container.remove();
							});
						} else {
							// always moves to last
							container.appendTo(container.parent());
						}
						node.on('click', launch).data('loading')();
						opts = {
							apiKey: self.confObj.apiKey,
							onSave: function(imageID, newURL) {
								var ext;
								featherEditor.showWaitIndicator();
								ext = newURL.replace(/.+\.([^.]+)$/, '$1');
								if (node.data('ext') !== ext) {
									node.closest('.ui-dialog').trigger('changeType', {
										extention: ext,
										mime : ext2mime[ext]
									});
								}
								node.on('load error', function() {
										node.data('loading')(true);
									})
									.attr('crossorigin', 'anonymous')
									.attr('src', newURL)
									.data('loading')();
								featherEditor.close();
							},
							onLoad: onload || function(){},
							onClose: function() { 
								dialog.removeClass(fm.res('class', 'preventback'));
								fm.toggleMaximize(container, false);
								$(container).hide();
							},
							appendTo: container.get(0),
							maxSize: 2048,
							language: getLang()
						};
						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: base,
							editorObj: Aviary,
							instance: void(0),
							opts: opts
						});
						featherEditor = new Aviary.Feather(opts);
						// return editor instance
						dfrd.resolve(featherEditor);
						$(base).on('saveAsFail', launch);
					},
					launch = function() {
						dialog.addClass(fm.res('class', 'preventback'));
						fm.toggleMaximize(container, true);
						fm.toFront(container);
						$(container).show();
						featherEditor.launch({
							image: node.attr('id'),
							url: node.attr('src')
						});
						node.data('loading')(true);
					},
					featherEditor, extraOpts;
				
				// load script then init
				if (typeof Aviary === 'undefined') {
					fm.loadScript(['https://dme0ih8comzn4.cloudfront.net/imaging/v3/editor.js'], function() {
						init(launch);
					}, {loadType: 'tag'});
				} else {
					init();
					launch();
				}
				return dfrd;
			},
			// Convert content url to data uri scheme to save content
			save : function(base) {
				var node = $(base).children('img:first');
				if (node.attr('src').substr(0, 5) !== 'data:') {
					node.attr('src', imgBase64(node, this.file.mime));
				}
			}
		},
		{
			// ACE Editor
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				if (fm.UA.ltIE8 || !fm.options.cdns.ace) {
					this.disabled = true;
				}
			},
			// `mimes` is not set for support everything kind of text file
			info : {
				id : 'aceeditor',
				name : 'ACE Editor',
				iconImg : 'img/editor-icons.png 0 -96'
			},
			load : function(textarea) {
				var self = this,
					fm   = this.fm,
					dfrd = $.Deferred(),
					cdn  = fm.options.cdns.ace,
					start = function() {
						var editor, editorBase, mode,
						ta = $(textarea),
						taBase = ta.parent(),
						dialog = taBase.parent(),
						id = textarea.id + '_ace',
						ext = self.file.name.replace(/^.+\.([^.]+)|(.+)$/, '$1$2').toLowerCase(),
						// MIME/mode map
						mimeMode = {
							'text/x-php'			  : 'php',
							'application/x-php'		  : 'php',
							'text/html'				  : 'html',
							'application/xhtml+xml'	  : 'html',
							'text/javascript'		  : 'javascript',
							'application/javascript'  : 'javascript',
							'text/css'				  : 'css',
							'text/x-c'				  : 'c_cpp',
							'text/x-csrc'			  : 'c_cpp',
							'text/x-chdr'			  : 'c_cpp',
							'text/x-c++'			  : 'c_cpp',
							'text/x-c++src'			  : 'c_cpp',
							'text/x-c++hdr'			  : 'c_cpp',
							'text/x-shellscript'	  : 'sh',
							'application/x-csh'		  : 'sh',
							'text/x-python'			  : 'python',
							'text/x-java'			  : 'java',
							'text/x-java-source'	  : 'java',
							'text/x-ruby'			  : 'ruby',
							'text/x-perl'			  : 'perl',
							'application/x-perl'	  : 'perl',
							'text/x-sql'			  : 'sql',
							'text/xml'				  : 'xml',
							'application/docbook+xml' : 'xml',
							'application/xml'		  : 'xml'
						};

						// set base height
						taBase.height(taBase.height());

						// set basePath of ace
						ace.config.set('basePath', cdn);

						// Base node of Ace editor
						editorBase = $('<div id="'+id+'" style="width:100%; height:100%;"/>').text(ta.val()).insertBefore(ta.hide());

						// Editor flag
						ta.data('ace', true);

						// Aceeditor instance
						editor = ace.edit(id);

						// Ace editor configure
						editor.$blockScrolling = Infinity;
						editor.setOptions({
							theme: 'ace/theme/monokai',
							fontSize: '14px',
							wrap: true,
						});
						ace.config.loadModule('ace/ext/modelist', function() {
							// detect mode
							mode = ace.require('ace/ext/modelist').getModeForPath('/' + self.file.name).name;
							if (mode === 'text') {
								if (mimeMode[self.file.mime]) {
									mode = mimeMode[self.file.mime];
								}
							}
							// show MIME:mode in title bar
							taBase.prev().children('.elfinder-dialog-title').append(' (' + self.file.mime + ' : ' + mode.split(/[\/\\]/).pop() + ')');
							editor.setOptions({
								mode: 'ace/mode/' + mode
							});
							if (dfrd.state() === 'resolved') {
								dialog.trigger('resize');
							}
						});
						ace.config.loadModule('ace/ext/language_tools', function() {
							ace.require('ace/ext/language_tools');
							editor.setOptions({
								enableBasicAutocompletion: true,
								enableSnippets: true,
								enableLiveAutocompletion: false
							});
						});
						ace.config.loadModule('ace/ext/settings_menu', function() {
							ace.require('ace/ext/settings_menu').init(editor);
						});
						
						// Short cuts
						editor.commands.addCommand({
							name : "saveFile",
							bindKey: {
								win : 'Ctrl-s',
								mac : 'Command-s'
							},
							exec: function(editor) {
								self.doSave();
							}
						});
						editor.commands.addCommand({
							name : "closeEditor",
							bindKey: {
								win : 'Ctrl-w|Ctrl-q',
								mac : 'Command-w|Command-q'
							},
							exec: function(editor) {
								self.doCancel();
							}
						});

						editor.resize();

						// TextArea button and Setting button
						$('<div class="ui-dialog-buttonset"/>').css('float', 'left')
						.append(
							$('<button/>').html(self.fm.i18n('TextArea'))
							.button()
							.on('click', function(){
								if (ta.data('ace')) {
									ta.removeData('ace');
									editorBase.hide();
									ta.val(editor.session.getValue()).show().trigger('focus');
									$(this).text('AceEditor');
								} else {
									ta.data('ace', true);
									editorBase.show();
									editor.setValue(ta.hide().val(), -1);
									editor.focus();
									$(this).html(self.fm.i18n('TextArea'));
								}
							})
						)
						.append(
							$('<button>Ace editor setting</button>')
							.button({
								icons: {
									primary: 'ui-icon-gear',
									secondary: 'ui-icon-triangle-1-e'
								},
								text: false
							})
							.on('click', function(){
								editor.showSettingsMenu();
								$('#ace_settingsmenu')
									.css('font-size', '80%')
									.find('div[contains="setOptions"]').hide().end()
									.parent().parent().appendTo($('#elfinder'));
							})
						)
						.prependTo(taBase.next());

						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: textarea,
							editorObj: ace,
							instance: editor,
							opts: {}
						});
						
						//dialog.trigger('resize');
						dfrd.resolve(editor);
					};

				// check ace & start
				if (!self.confObj.loader) {
					self.confObj.loader = $.Deferred();
					self.fm.loadScript([ cdn+'/ace.js' ], function() {
						self.confObj.loader.resolve();
					}, void 0, {obj: window, name: 'ace'});
				}
				self.confObj.loader.done(start);

				return dfrd;
			},
			close : function(textarea, instance) {
				instance && instance.destroy();
			},
			save : function(textarea, instance) {
				instance && $(textarea).data('ace') && (textarea.value = instance.session.getValue());
			},
			focus : function(textarea, instance) {
				instance && $(textarea).data('ace') && instance.focus();
			},
			resize : function(textarea, instance, e, data) {
				instance && instance.resize();
			}
		},
		{
			// CodeMirror
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				if (fm.UA.ltIE10 || !fm.options.cdns.codemirror) {
					this.disabled = true;
				}
			},
			// `mimes` is not set for support everything kind of text file
			info : {
				id : 'codemirror',
				name : 'CodeMirror',
				iconImg : 'img/editor-icons.png 0 -176'
			},
			load : function(textarea) {
				var fm = this.fm,
					cmUrl = fm.options.cdns.codemirror,
					dfrd = $.Deferred(),
					self = this,
					start = function(CodeMirror) {
						var ta   = $(textarea),
							base = ta.parent(),
							editor, editorBase, opts;
						
						// set base height
						base.height(base.height());
						
						// CodeMirror configure options
						opts = {
							lineNumbers: true,
							lineWrapping: true,
							extraKeys : {
								'Ctrl-S': function() { self.doSave(); },
								'Ctrl-Q': function() { self.doCancel(); },
								'Ctrl-W': function() { self.doCancel(); }
							}
						};

						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: textarea,
							editorObj: CodeMirror,
							instance: void(0),
							opts: opts
						});

						// CodeMirror configure
						editor = CodeMirror.fromTextArea(textarea, opts);
						
						// return editor instance
						dfrd.resolve(editor);
						
						// Auto mode set
						var info, m, mode, spec;
						if (! info) {
							info = CodeMirror.findModeByMIME(self.file.mime);
						}
						if (! info && (m = self.file.name.match(/.+\.([^.]+)$/))) {
							info = CodeMirror.findModeByExtension(m[1]);
						}
						if (info) {
							CodeMirror.modeURL = useRequire? 'codemirror/mode/%N/%N.min' : cmUrl + '/mode/%N/%N.min.js';
							mode = info.mode;
							spec = info.mime;
							editor.setOption('mode', spec);
							CodeMirror.autoLoadMode(editor, mode);
							// show MIME:mode in title bar
							base.prev().children('.elfinder-dialog-title').append(' (' + spec + ' : ' + mode + ')');
						}
						
						// editor base node
						editorBase = $(editor.getWrapperElement()).css({
							// fix CSS conflict to SimpleMDE
							padding: 0,
							border: 'none'
						});
						ta.data('cm', true);
						
						// fit height to base
						editorBase.height('100%');
						
						// TextArea button and Setting button
						$('<div class="ui-dialog-buttonset"/>').css('float', 'left')
						.append(
							$('<button/>').html(self.fm.i18n('TextArea'))
							.button()
							.on('click', function(){
								if (ta.data('cm')) {
									ta.removeData('cm');
									editorBase.hide();
									ta.val(editor.getValue()).show().trigger('focus');
									$(this).text('CodeMirror');
								} else {
									ta.data('cm', true);
									editorBase.show();
									editor.setValue(ta.hide().val());
									editor.refresh();
									editor.focus();
									$(this).html(self.fm.i18n('TextArea'));
								}
							})
						)
						.prependTo(base.next());
					};
				// load script then start
				if (!self.confObj.loader) {
					self.confObj.loader = $.Deferred();
					if (useRequire) {
						require.config({
							packages: [{
								name: 'codemirror',
								location: cmUrl,
								main: 'codemirror.min'
							}],
							map: {
								'codemirror': {
									'codemirror/lib/codemirror': 'codemirror'
								}
							}
						});
						require([
							'codemirror',
							'codemirror/addon/mode/loadmode.min',
							'codemirror/mode/meta.min'
						], function(CodeMirror) {
							self.confObj.loader.resolve(CodeMirror);
						});
					} else {
						self.fm.loadScript([
							cmUrl + '/codemirror.min.js'
						], function() {
							self.fm.loadScript([
								cmUrl + '/addon/mode/loadmode.min.js',
								cmUrl + '/mode/meta.min.js'
							], function() {
								self.confObj.loader.resolve(CodeMirror);
							});
						}, {loadType: 'tag'});
					}
					self.fm.loadCss(cmUrl + '/codemirror.css');
				}
				self.confObj.loader.done(start);
				return dfrd;
			},
			close : function(textarea, instance) {
				instance && instance.toTextArea();
			},
			save : function(textarea, instance) {
				instance && $(textarea).data('cm') && (textarea.value = instance.getValue());
			},
			focus : function(textarea, instance) {
				instance && $(textarea).data('cm') && instance.focus();
			},
			resize : function(textarea, instance, e, data) {
				instance && instance.refresh();
			}
		},
		{
			// SimpleMDE
			// called on initialization of elFinder cmd edit (this: this editor's config object)
			setup : function(opts, fm) {
				if (fm.UA.ltIE10 || !fm.options.cdns.simplemde) {
					this.disabled = true;
				}
			},
			info : {
				id : 'simplemde',
				name : 'SimpleMDE',
				iconImg : 'img/editor-icons.png 0 -80'
			},
			exts  : ['md'],
			load : function(textarea) {
				var self = this,
					fm   = this.fm,
					base = $(textarea).parent(),
					dfrd = $.Deferred(),
					cdn  = fm.options.cdns.simplemde,
					start = function(SimpleMDE) {
						var h	 = base.height(),
							delta = base.outerHeight(true) - h + 14,
							editor, editorBase, opts;
						
						// fit height function
						textarea._setHeight = function(height) {
							var h	= height || base.height(),
								ctrH = 0,
								areaH;
							base.children('.editor-toolbar,.editor-statusbar').each(function() {
								ctrH += $(this).outerHeight(true);
							});
							areaH = h - ctrH - delta;
							editorBase.height(areaH);
							editor.codemirror.refresh();
							return areaH;
						};
						
						// set base height
						base.height(h);
						
						opts = {
							element: textarea,
							autofocus: true
						};

						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: textarea,
							editorObj: SimpleMDE,
							instance: void(0),
							opts: opts
						});

						// make editor
						editor = new SimpleMDE(opts);
						dfrd.resolve(editor);
						
						// editor base node
						editorBase = $(editor.codemirror.getWrapperElement());
						
						// fit height to base
						editorBase.css('min-height', '50px')
							.children('.CodeMirror-scroll').css('min-height', '50px');
						textarea._setHeight(h);
					};

				// check SimpleMDE & start
				if (!self.confObj.loader) {
					self.confObj.loader = $.Deferred();
					self.fm.loadCss(cdn+'/simplemde.min.css');
					if (useRequire) {
						require([
							cdn+'/simplemde.min.js'
						], function(SimpleMDE) {
							self.confObj.loader.resolve(SimpleMDE);
						});
					} else {
						self.fm.loadScript([cdn+'/simplemde.min.js'], function() {
							self.confObj.loader.resolve(SimpleMDE);
						}, {loadType: 'tag'});
					}
				}
				self.confObj.loader.done(start);

				return dfrd;
			},
			close : function(textarea, instance) {
				instance && instance.toTextArea();
				instance = null;
			},
			save : function(textarea, instance) {
				instance && (textarea.value = instance.value());
			},
			focus : function(textarea, instance) {
				instance && instance.codemirror.focus();
			},
			resize : function(textarea, instance, e, data) {
				instance && textarea._setHeight();
			}
		},
		{
			// CKEditor for html file
			info : {
				id : 'ckeditor',
				name : 'CKEditor',
				iconImg : 'img/editor-icons.png 0 0'
			},
			exts  : ['htm', 'html', 'xhtml'],
			setup : function(opts, fm) {
				if (!fm.options.cdns.ckeditor) {
					this.disabled = true;
				} else {
					if (opts.extraOptions && opts.extraOptions.managerUrl) {
						this.managerUrl = opts.extraOptions.managerUrl;
					}
				}
			},
			load : function(textarea) {
				var self = this,
					fm   = this.fm,
					dfrd = $.Deferred(),
					init = function() {
						var base = $(textarea).parent(),
							dlg = base.closest('.elfinder-dialog'),
							h = base.height(),
							reg = /([&?]getfile=)[^&]+/,
							loc = self.confObj.managerUrl || window.location.href.replace(/#.*$/, ''),
							name = 'ckeditor',
							opts;
						
						// make manager location
						if (reg.test(loc)) {
							loc = loc.replace(reg, '$1' + name);
						} else {
							loc += '?getfile=' + name;
						}
						// set base height
						base.height(h);

						// CKEditor configure options
						opts = {
							startupFocus : true,
							fullPage: true,
							allowedContent: true,
							filebrowserBrowseUrl : loc,
							toolbarCanCollapse: true,
							toolbarStartupExpanded: !fm.UA.Mobile,
							removePlugins: 'resize',
							extraPlugins: 'colorbutton,justify,docprops',
							on: {
								'instanceReady' : function(e) {
									var editor = e.editor;
									editor.resize('100%', h);
									// re-build on dom move
									dlg.one('beforedommove.'+fm.namespace, function() {
										editor.destroy();
									}).one('dommove.'+fm.namespace, function() {
										self.load(textarea).done(function(editor) {
											self.instance = editor;
										});
									});
									// return editor instance
									dfrd.resolve(e.editor);
								}
							}
						};

						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: textarea,
							editorObj: CKEDITOR,
							instance: void(0),
							opts: opts
						});

						// CKEditor configure
						CKEDITOR.replace(textarea.id, opts);
						CKEDITOR.on('dialogDefinition', function(e) {
							var dlg = e.data.definition.dialog;
							dlg.on('show', function(e) {
								fm.getUI().append($('.cke_dialog_background_cover')).append(this.getElement().$);
							});
							dlg.on('hide', function(e) {
								$('body:first').append($('.cke_dialog_background_cover')).append(this.getElement().$);
							});
						});
					};

				if (!self.confObj.loader) {
					self.confObj.loader = $.Deferred();
					window.CKEDITOR_BASEPATH = fm.options.cdns.ckeditor + '/';
					$.getScript(fm.options.cdns.ckeditor + '/ckeditor.js', function() {
						self.confObj.loader.resolve();
					});
				}
				self.confObj.loader.done(init);
				return dfrd;
			},
			close : function(textarea, instance) {
				instance && instance.destroy();
			},
			save : function(textarea, instance) {
				instance && (textarea.value = instance.getData());
			},
			focus : function(textarea, instance) {
				instance && instance.focus();
			},
			resize : function(textarea, instance, e, data) {
				var self;
				if (instance) {
					if (instance.status === 'ready') {
						instance.resize('100%', $(textarea).parent().height());
					}
				}
			}
		},
		{
			// CKEditor5 balloon mode for html file
			info : {
				id : 'ckeditor5',
				name : 'CKEditor5',
				iconImg : 'img/editor-icons.png 0 -16'
			},
			exts : ['htm', 'html', 'xhtml'],
			html : '<div class="edit-editor-ckeditor5"></div>',
			setup : function(opts, fm) {
				var confObj = this;
				// check cdn and ES6 support
				if (!fm.options.cdns.ckeditor5 || typeof window.Symbol !== 'function' || typeof Symbol() !== 'symbol') {
					this.disabled = true;
				} else {
					if (opts.extraOptions && opts.extraOptions.ckeditor5Mode) {
						this.ckeditor5Mode = opts.extraOptions.ckeditor5Mode;
					}
				}
				fm.bind('destroy', function() {
					confObj.editor = null;
				});
			},
			// Prepare on before show dialog
			prepare : function(base, dialogOpts, file) {
				$(base).height(base.editor.fm.getUI().height() - 100);
			},
			init : function(id, file, data, fm) {
				var m = data.match(/^([\s\S]*<body[^>]*>)([\s\S]+)(<\/body>[\s\S]*)$/i),
					header = '',
					body = '',
					footer ='';
				this.css({
					width: '100%',
					height: '100%',
					'box-sizing': 'border-box'
				});
				if (m) {
					header = m[1];
					body = m[2];
					footer = m[3];
				} else {
					body = data;
				}
				this.data('data', {
					header: header,
					body: body,
					footer: footer
				});
			},
			load : function(editnode) {
				var self = this,
					fm   = this.fm,
					dfrd = $.Deferred(),
					mode = self.confObj.ckeditor5Mode || 'balloon',
					lang = (function() {
						var l = fm.lang.toLowerCase().replace('_', '-');
						if (l.substr(0, 2) === 'zh' && l !== 'zh-cn') {
							l = 'zh';
						}
						return l;
					})(),
					init = function(cEditor) {
						var base = $(editnode).parent(),
							opts;
						
						// set base height
						base.height(fm.getUI().height() - 100);

						// CKEditor5 configure options
						opts = {
							toolbar: ['heading', '|', 'bold', 'italic', 'link', 'imageUpload', 'bulletedList', 'numberedList', 'blockQuote', 'undo', 'redo' ],
							language: lang
						};

						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: editnode,
							editorObj: cEditor,
							instance: void(0),
							opts: opts
						});

						cEditor
							.create(editnode, opts)
							.then(function(editor) {
								var fileRepo = editor.plugins.get('FileRepository');
								fileRepo.createUploadAdapter = function(loader) {
									return new uploder(loader);
								};
								editor.setData($(editnode).data('data').body);
								// move .ck-body to elFinder node for fullscreen mode
								fm.getUI().append($('body > div.ck-body'));
								$('div.ck-balloon-panel').css({
									'z-index': fm.getMaximizeCss().zIndex + 1
								});
								dfrd.resolve(editor);
								/*fm.log({
									plugins: cEditor.build.plugins.map(function(p) { return p.pluginName; }),
									toolbars: Array.from(editor.ui.componentFactory.names())
								});*/
							})
							['catch'](function(error) { // ['cache'] instead .cache for fix error on ie8 
								fm.error(error);
							});
					},
					uploder = function(loader) {
						this.upload = function() {
							return new Promise(function(resolve, reject) {
								fm.exec('upload', {files: [loader.file]}, void(0), fm.cwd().hash)
									.done(function(data){
										if (data.added && data.added.length) {
											fm.url(data.added[0].hash, { async: true }).done(function(url) {
												resolve({
													'default': fm.convAbsUrl(url)
												});
											}).fail(function() {
												reject('errFileNotFound');
											});
										} else {
											reject(fm.i18n(data.error? data.error : 'errUpload'));
										}
									})
									.fail(function(error) {
										reject(fm.i18n(error? (error === 'userabort'? 'errAbort' : error) : 'errUploadNoFiles'));
									})
									.progress(function(data) {
										loader.uploadTotal = data.total;
										loader.uploaded = data.progress;
									});
							});
						};
						this.abort = function() {
							fm.getUI().trigger('uploadabort');
						};
					}, loader;

				if (!self.confObj.editor) {
					loader = $.Deferred();
					self.fm.loadScript([
						fm.options.cdns.ckeditor5 + '/' + mode + '/ckeditor.js'
					], function(editor) {
						if (!editor) {
							editor = window.BalloonEditor || window.InlineEditor || window.ClassicEditor;
						}
						if (fm.lang !== 'en') {
							self.fm.loadScript([
								fm.options.cdns.ckeditor5 + '/' + mode + '/translations/' + lang + '.js'
							], function(obj) {
								loader.resolve(editor);
							}, {
								tryRequire: true,
								loadType: 'tag',
								error: function(obj) {
									lang = 'en';
									loader.resolve(editor);
								}
							});
						} else {
							loader.resolve(editor);
						}
					}, {
						tryRequire: true,
						loadType: 'tag'
					});
					loader.done(function(editor) {
						self.confObj.editor = editor;
						init(editor);
					});
				} else {
					init(self.confObj.editor);
				}
				return dfrd;
			},
			getContent : function() {
				var data = $(this).data('data');
				return data.header + data.body + data.footer;
			},
			close : function(editnode, instance) {
				instance && instance.destroy();
			},
			save : function(editnode, instance) {
				var elm = $(editnode),
					data = elm.data('data');
				if (instance) {
					data.body = instance.getData();
					elm.data('data', data);
				}
			},
			focus : function(editnode, instance) {
				$(editnode).trigger('focus');
			}
		},
		{
			// TinyMCE for html file
			info : {
				id : 'tinymce',
				name : 'TinyMCE',
				iconImg : 'img/editor-icons.png 0 -64'
			},
			exts  : ['htm', 'html', 'xhtml'],
			setup : function(opts, fm) {
				if (!fm.options.cdns.tinymce) {
					this.disabled = true;
				} else {
					if (opts.extraOptions && opts.extraOptions.managerUrl) {
						this.managerUrl = opts.extraOptions.managerUrl;
					}
				}
			},
			load : function(textarea) {
				var self = this,
					fm   = this.fm,
					dfrd = $.Deferred(),
					init = function() {
						var base = $(textarea).show().parent(),
							dlg = base.closest('.elfinder-dialog'),
							h = base.height(),
							delta = base.outerHeight(true) - h,
							opts;

						// set base height
						base.height(h);
						// fit height function
						textarea._setHeight = function(height) {
							var base = $(this).parent(),
								h	= height || base.height(),
								ctrH = 0,
								areaH;
							base.find('.mce-container-body:first').children('.mce-top-part,.mce-statusbar').each(function() {
								ctrH += $(this).outerHeight(true);
							});
							areaH = h - ctrH - delta;
							base.find('.mce-edit-area iframe:first').height(areaH);
							return areaH;
						};

						// TinyMCE configure options
						opts = {
							selector: '#' + textarea.id,
							resize: false,
							plugins: [
								'fullpage', // require for getting full HTML
								'image', 'link', 'media',
								'code', 'fullscreen'
							],
							init_instance_callback : function(editor) {
								// fit height on init
								textarea._setHeight(h);
								// re-build on dom move
								dlg.one('beforedommove.'+fm.namespace, function() {
									tinymce.execCommand('mceRemoveEditor', false, textarea.id);
								}).one('dommove.'+fm.namespace, function() {
									self.load(textarea).done(function(editor) {
										self.instance = editor;
									});
								});
								// return editor instance
								dfrd.resolve(editor);
							},
							file_picker_callback : function (callback, value, meta) {
								var reg = /([&?]getfile=)[^&]+/,
									loc = self.confObj.managerUrl || window.location.href.replace(/#.*$/, ''),
									name = 'tinymce';
								
								// make manager location
								if (reg.test(loc)) {
									loc = loc.replace(reg, '$1' + name);
								} else {
									loc += '?getfile=' + name;
								}
								// launch TinyMCE
								tinymce.activeEditor.windowManager.open({
									file: loc,
									title: 'elFinder',
									width: 900,	 
									height: 450,
									resizable: 'yes'
								}, {
									oninsert: function (file, elf) {
										var url, reg, info;

										// URL normalization
										url = elf.convAbsUrl(file.url);
										
										// Make file info
										info = file.name + ' (' + elf.formatSize(file.size) + ')';

										// Provide file and text for the link dialog
										if (meta.filetype == 'file') {
											callback(url, {text: info, title: info});
										}

										// Provide image and alt text for the image dialog
										if (meta.filetype == 'image') {
											callback(url, {alt: info});
										}

										// Provide alternative source and posted for the media dialog
										if (meta.filetype == 'media') {
											callback(url);
										}
									}
								});
								return false;
							}
						};

						// trigger event 'editEditorPrepare'
						self.trigger('Prepare', {
							node: textarea,
							editorObj: tinymce,
							instance: void(0),
							opts: opts
						});

						// TinyMCE configure
						tinymce.init(opts);
					};
				
				if (!self.confObj.loader) {
					self.confObj.loader = $.Deferred();
					$.getScript(fm.options.cdns.tinymce + '/tinymce.min.js', function() {
						setTimeout(function() {
							self.confObj.loader.resolve();
						}, 0);
					});
				}
				self.confObj.loader.done(init);
				return dfrd;
			},
			close : function(textarea, instance) {
				instance && tinymce.execCommand('mceRemoveEditor', false, textarea.id);
			},
			save : function(textarea, instance) {
				instance && instance.save();
			},
			focus : function(textarea, instance) {
				instance && instance.focus();
			},
			resize : function(textarea, instance, e, data) {
				// fit height to base node on dialog resize
				instance && textarea._setHeight();
			}
		},
		{
			info : {
				id : 'zohoeditor',
				name : 'Zoho Editor',
				iconImg : 'img/editor-icons.png 0 -32',
				cmdCheck : 'ZohoOffice',
				preventGet: true,
				hideButtons: true,
				syncInterval : 15000,
				canMakeEmpty: true,
				integrate: {
					title: 'Zoho Office API',
					link: 'https://www.zoho.com/officeapi/'
				}
			},
			mimes : [
				'application/msword',
				'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
				//'application/pdf',
				'application/vnd.oasis.opendocument.text',
				'application/rtf',
				'text/html',
				'application/vnd.ms-excel',
				'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
				'application/vnd.oasis.opendocument.spreadsheet',
				'application/vnd.sun.xml.calc',
				'text/csv',
				'text/tab-separated-values',
				'application/vnd.ms-powerpoint',
				'application/vnd.openxmlformats-officedocument.presentationml.presentation',
				'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
				'application/vnd.oasis.opendocument.presentation',
				'application/vnd.sun.xml.impress'
			],
			html : '<iframe style="width:100%;max-height:100%;border:none;"></iframe>',
			// setup on elFinder bootup
			setup : function(opts, fm) {
				if (fm.UA.Mobile || fm.UA.ltIE8) {
					this.disabled = true;
				}
			},
			// Prepare on before show dialog
			prepare : function(base, dialogOpts, file) {
				var elfNode = base.editor.fm.getUI();
				$(base).height(elfNode.height());
				dialogOpts.width = Math.max(dialogOpts.width || 0, elfNode.width() * 0.8);
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, dum, fm) {
				var ta = this,
					ifm = $(this).hide(),
					spnr = $('<div/>')
						.css({
							position: 'absolute',
							top: '50%',
							textAlign: 'center',
							width: '100%',
							fontSize: '16pt'
						})
						.html(fm.i18n('nowLoading') + '<span class="elfinder-spinner"/>')
						.appendTo(ifm.parent()),
					cdata = function() {
						var data = '';
						$.each(fm.customData, function(key, val) {
							data += '&' + encodeURIComponent(key) + '=' + encodeURIComponent(val);
						});
						return data;
					};
				
				$(ta).data('xhr', fm.request({
					data: {
						cmd: 'editor',
						name: 'ZohoOffice',
						method: 'init',
						'args[target]': file.hash,
						'args[lang]' : fm.lang,
						'args[cdata]' : cdata
					},
					preventDefault : true
				}).done(function(data) {
					var opts;
					if (data.zohourl) {
						opts = {
							css: {
								height: '100%'
							}
						};
						// trigger event 'editEditorPrepare'
						ta.editor.trigger('Prepare', {
							node: ta,
							editorObj: void(0),
							instance: ifm,
							opts: opts
						});

						ifm.attr('src', data.zohourl).show().css(opts.css);
					} else {
						data.error && fm.error(data.error);
						ta.elfinderdialog('destroy');
					}
				}).fail(function(error) {
					error && fm.error(error);
					ta.elfinderdialog('destroy');
				}).always(function() {
					spnr.remove();
				}));
			},
			load : function() {},
			getContent : function() {},
			save : function() {},
			// Before dialog close
			beforeclose : iframeClose,
			// On dialog closed
			close : function(ta) {
				var fm = this.fm,
					xhr = $(ta).data('xhr');
				if (xhr.state() === 'pending') {
					xhr.reject();
				}
			}
		},
		{
			// Zip Archive with FlySystem
			info : {
				id : 'ziparchive',
				name : 'btnMount',
				iconImg : 'img/toolbar.png 0 -416',
				cmdCheck : 'ZipArchive',
				edit : function(file, editor) {
					var fm = this,
						dfrd = $.Deferred();
					fm.request({
						data:{
							cmd: 'netmount',
							protocol: 'ziparchive',
							host: file.hash,
							path: file.phash
						},
						notify : {type : 'netmount', cnt : 1, hideCnt : true}
					}).done(function(data) {
						var pdir;
						if (data.added && data.added.length) {
							if (data.added[0].phash) {
								if (pdir = fm.file(data.added[0].phash)) {
									if (! pdir.dirs) {
										pdir.dirs = 1;
										fm.change({ changed: [ pdir ] });
									}
								}
							}
							fm.one('netmountdone', function() {
								fm.exec('open', data.added[0].hash);
								fm.one('opendone', function() {
									data.toast && fm.toast(data.toast);
								});
							});
						}
						dfrd.resolve();
					})
					.fail(function(error) {
						dfrd.reject(error);
					});
					return dfrd;
				}
			},
			mimes : ['application/zip'],
			load : function() {},
			save : function(){}
		},
		{
			// Simple Text (basic textarea editor)
			info : {
				id : 'textarea',
				name : 'TextArea',
				useTextAreaEvent : true
			},
			load : function(textarea) {
				// trigger event 'editEditorPrepare'
				this.trigger('Prepare', {
					node: textarea,
					editorObj: void(0),
					instance: void(0),
					opts: {}
				});
				textarea.setSelectionRange && textarea.setSelectionRange(0, 0);
				$(textarea).trigger('focus').show();
			},
			save : function(){}
		},
		{
			// File converter with online-convert.com
			info : {
				id : 'onlineconvert',
				name : 'Online Convert',
				iconImg : 'img/editor-icons.png 0 -144',
				cmdCheck : 'OnlineConvert',
				preventGet: true,
				hideButtons: true,
				single: true,
				converter: true,
				canMakeEmpty: false,
				integrate: {
					title: 'ONLINE-CONVERT.COM',
					link: 'https://online-convert.com'
				}
			},
			mimes : ['*'],
			html : '<iframe style="width:100%;max-height:100%;border:none;"></iframe>',
			// setup on elFinder bootup
			setup : function(opts, fm) {
				var mOpts = opts.extraOptions.onlineConvert || {maxSize:100,showLink:true};
				if (mOpts.maxSize) {
					this.info.maxSize = mOpts.maxSize * 1048576;
				}
				this.set = Object.assign({
					url : 'https://%s.online-convert.com%s?external_url=',
					conv : {
						Archive: {'7Z':{}, 'BZ2':{ext:'bz'}, 'GZ':{}, 'ZIP':{}},
						Audio: {'MP3':{}, 'OGG':{ext:'oga'}, 'WAV':{}, 'WMA':{}, 'AAC':{}, 'AIFF':{ext:'aif'}, 'FLAC':{}, 'M4A':{}, 'MMF':{}, 'OPUS':{ext:'oga'}},
						Document: {'DOC':{}, 'DOCX':{}, 'HTML':{}, 'ODT':{}, 'PDF':{}, 'PPT':{}, 'PPTX':{}, 'RTF':{}, 'SWF':{}, 'TXT':{}},
						eBook: {'AZW3':{ext:'azw'}, 'ePub':{}, 'FB2':{ext:'xml'}, 'LIT':{}, 'LRF':{}, 'MOBI':{}, 'PDB':{}, 'PDF':{},'PDF-eBook':{ext:'pdf'}, 'TCR':{}},
						Hash: {'Adler32':{},  'Apache-htpasswd':{}, 'Blowfish':{}, 'CRC32':{}, 'CRC32B':{}, 'Gost':{}, 'Haval128':{},'MD4':{}, 'MD5':{}, 'RIPEMD128':{}, 'RIPEMD160':{}, 'SHA1':{}, 'SHA256':{}, 'SHA384':{}, 'SHA512':{}, 'Snefru':{}, 'Std-DES':{}, 'Tiger128':{}, 'Tiger128-calculator':{}, 'Tiger128-converter':{}, 'Tiger160':{}, 'Tiger192':{}, 'Whirlpool':{}},
						Image: {'BMP':{}, 'EPS':{ext:'ai'}, 'GIF':{}, 'EXR':{}, 'ICO':{}, 'JPG':{}, 'PNG':{}, 'SVG':{}, 'TGA':{}, 'TIFF':{ext:'tif'}, 'WBMP':{}, 'WebP':{}},
						Video: {'3G2':{}, '3GP':{}, 'AVI':{}, 'FLV':{}, 'HLS':{ext:'m3u8'}, 'MKV':{}, 'MOV':{}, 'MP4':{}, 'MPEG-1':{ext:'mpeg'}, 'MPEG-2':{ext:'mpeg'}, 'OGG':{ext:'ogv'}, 'OGV':{}, 'WebM':{}, 'WMV':{}, 'Android':{link:'/convert-video-for-%s',ext:'mp4'}, 'Blackberry':{link:'/convert-video-for-%s',ext:'mp4'}, 'DPG':{link:'/convert-video-for-%s',ext:'avi'}, 'iPad':{link:'/convert-video-for-%s',ext:'mp4'}, 'iPhone':{link:'/convert-video-for-%s',ext:'mp4'}, 'iPod':{link:'/convert-video-for-%s',ext:'mp4'}, 'Nintendo-3DS':{link:'/convert-video-for-%s',ext:'avi'}, 'Nintendo-DS':{link:'/convert-video-for-%s',ext:'avi'}, 'PS3':{link:'/convert-video-for-%s',ext:'mp4'}, 'Wii':{link:'/convert-video-for-%s',ext:'avi'}, 'Xbox':{link:'/convert-video-for-%s',ext:'wmv'}}
					},
					catExts : {
						Hash: 'txt'
					},
					link : '<div class="elfinder-edit-onlineconvert-link"><a href="https://www.online-convert.com" target="_blank"><span class="elfinder-button-icon"></span>ONLINE-CONVERT.COM</a></div>',
					toastWidth : 280,
					useTabs : ($.fn.tabs && !fm.UA.iOS)? true : false // Can't work on iOS, I don't know why.
				}, mOpts);
			},
			// Prepare on before show dialog
			prepare : function(base, dialogOpts, file) {
				var elfNode = base.editor.fm.getUI();
				$(base).height(elfNode.height());
				dialogOpts.width = Math.max(dialogOpts.width || 0, elfNode.width() * 0.8);
			},
			// Initialization of editing node (this: this editors HTML node)
			init : function(id, file, dum, fm) {
				var ta = this,
					confObj = ta.editor.confObj,
					set = confObj.set,
					uiToast = fm.getUI('toast'),
					idxs = {},
					allowZip = fm.uploadMimeCheck('application/zip', file.phash),
					getExt = function(cat, con) {
						var c;
						if (set.catExts[cat]) {
							return set.catExts[cat];
						}
						if (set.conv[cat] && (c = set.conv[cat][con])) {
							return (c.ext || con).toLowerCase();
						}
						return con.toLowerCase();
					},
					setOptions = function(cat, done) {
						var type, dfdInit, dfd;
						if (typeof confObj.api === 'undefined') {
							dfdInit = fm.request({
								data: {
									cmd: 'editor',
									name: 'OnlineConvert',
									method: 'init'
								},
								preventDefault : true
							});
						} else {
							dfdInit = $.Deferred().resolve({api: confObj.api});
						}
						cat = cat.toLowerCase();
						dfdInit.done(function(data) {
							confObj.api = data.api;
							if (confObj.api) {
								if (cat) {
									type = '?category=' + cat;
								} else {
									type = '';
									cat = 'all';
								}
								if (!confObj.conversions) {
									confObj.conversions = {};
								}
								if (!confObj.conversions[cat]) {
									dfd = $.getJSON('https://api2.online-convert.com/conversions' + type);
								} else {
									dfd = $.Deferred().resolve(confObj.conversions[cat]);
								}
								dfd.done(function(d) {
									confObj.conversions[cat] = d;
									$.each(d, function(i, o) {
										btns[set.useTabs? 'children' : 'find']('.onlineconvert-category-' + o.category).children('.onlineconvert-' + o.target).trigger('makeoption', o);
									});
									done && done();
								});
							}
						});
					},
					btns = (function() {
						var btns = $('<div/>').on('click', 'button', function() {
								var b = $(this),
									opts = b.data('opts') || null,
									cat = b.closest('.onlineconvert-category').data('cname'),
									con = b.data('conv');
								if (confObj.api === true) {
									api({
										category: cat,
										convert: con,
										options: opts
									});
								} else {
									open(cat, con);
								}
							}).on('change', function(e) {
								var t = $(e.target),
									p = t.parent(), 
									b = t.closest('.elfinder-edit-onlineconvert-button').children('button:first'),
									o = b.data('opts') || {},
									v = p.data('type') === 'boolean'? t.is(':checked') : t.val();
								e.stopPropagation();
								if (v) {
									if (p.data('type') === 'integer') {
										v = parseInt(v);
									}
									if (p.data('pattern')) {
										var reg = new RegExp(p.data('pattern'));
										if (!reg.test(v)) {
											requestAnimationFrame(function() {
												fm.error('"' + fm.escape(v) + '" is not match to "/' + fm.escape(p.data('pattern')) + '/"');
											});
											v = null;
										}
									}
								}
								if (v) {
									o[t.parent().data('optkey')] = v;
								} else {
									delete o[p.data('optkey')];
								}
								b.data('opts', o);
							}),
							ul = $('<ul/>'),
							oform = function(n, o) {
								var f = $('<p/>').data('optkey', n).data('type', o.type),
									checked = '',
									disabled = '',
									nozip = false,
									opts, btn, elm;
								if (o.description) {
									f.attr('title', fm.i18n(o.description));
								}
								if (o.pattern) {
									f.data('pattern', o.pattern);
								}
								f.append($('<span/>').text(fm.i18n(n) + ' : '));
								if (o.type === 'boolean') {
									if (o['default'] || (nozip = (n === 'allow_multiple_outputs' && !allowZip))) {
										checked = ' checked';
										if (nozip) {
											disabled = ' disabled';
										}
										btn = this.children('button:first');
										opts = btn.data('opts') || {};
										opts[n] = true;
										btn.data('opts', opts);
									}
									f.append($('<input type="checkbox" value="true"'+checked+disabled+'/>'));
								} else if (o['enum']){
									elm = $('<select/>').append($('<option value=""/>').text('Select...'));
									$.each(o['enum'], function(i, v) {
										elm.append($('<option value="'+v+'"/>').text(v));
									});
									f.append(elm);
								} else {
									f.append($('<input type="text" value=""/>'));
								}
								return f;
							},
							makeOption = function(o) {
								var elm = this,
									b = $('<span class="elfinder-button-icon elfinder-button-icon-preference"/>').on('click', function() {
										f.toggle();
									}),
									f = $('<div class="elfinder-edit-onlinconvert-options"/>').hide();
								if (o.options) {
									$.each(o.options, function(k, v) {
										k !== 'download_password' && f.append(oform.call(elm, k, v));
									});
								}
								elm.append(b, f);
							},
							ts = (+new Date()),
							i = 0;
						
						if (!confObj.ext2mime) {
							confObj.ext2mime = fm.arrayFlip(fm.mimeTypes);
						}
						$.each(set.conv, function(t, c) {
							var cname = t.toLowerCase(),
								id = 'elfinder-edit-onlineconvert-' + cname + ts,
								type = $('<div id="' + id + '" class="onlineconvert-category onlineconvert-category-'+cname+'"/>').data('cname', t),
								cext;
							$.each(c, function(n, o) {
								var nl = n.toLowerCase(),
									ext = getExt(t, n);
								if (!confObj.ext2mime[ext]) {
									if (cname === 'audio' || cname === 'image' || cname === 'video') {
										confObj.ext2mime[ext] = cname + '/x-' + nl;
									} else {
										confObj.ext2mime[ext] = 'application/octet-stream';
									}
								}
								if (fm.uploadMimeCheck(confObj.ext2mime[ext], file.phash)) {
									type.append($('<div class="elfinder-edit-onlineconvert-button onlineconvert-'+nl+'"/>').on('makeoption', function(e, data) {
										var elm = $(this);
										if (!elm.children('.elfinder-button-icon-preference').length) {
											makeOption.call(elm, data);
										}
									}).append($('<button/>').text(n).data('conv', n)));
								}
							});
							if (type.children().length) {
								ul.append($('<li/>').append($('<a/>').attr('href', '#' + id).text(t)));
								btns.append(type);
								idxs[cname] = i++;
							}
						});
						if (set.useTabs) {
							btns.prepend(ul).tabs({
								beforeActivate: function(e, ui) {
									setOptions(ui.newPanel.data('cname'));
								}
							});
						} else {
							$.each(set.conv, function(t) {
								var tl = t.toLowerCase();
								btns.append($('<fieldset class="onlineconvert-fieldset-' + tl + '"/>').append($('<legend/>').text(t)).append(btns.children('.onlineconvert-category-' + tl)));
							});
						}
						return btns;
					})(),
					ifm = $(this).hide(),
					select = $('<div/>')
						.append(
							btns,
							$('<div class="elfinder-edit-onlineconvert-bottom-btn"/>').append(
								$('<button/>')
									.addClass(fm.UA.iOS? 'elfinder-button-ios-multiline' : '')
									.html(fm.i18n('convertOn', 'Online-Convert.com'))
									.on('click', function() {
										open();
									})
							),
							(set.showLink? $(set.link) : null)
						)
						.appendTo(ifm.parent().css({overflow: 'auto'})),
					spnr = $('<div class="elfinder-edit-spiner elfinder-edit-online-convert"/>')
						.hide()
						.css({
							position: 'absolute',
							top: '50%',
							textAlign: 'center',
							width: '100%',
							fontSize: '16pt'
						})
						.html('<span class="elfinder-edit-loadingmsg">' + fm.i18n('nowLoading') + '</span><span class="elfinder-spinner"/>')
						.appendTo(ifm.parent()),
					_url = null,
					url = function() {
						if (_url) {
							return $.Deferred().resolve(_url);
						} else {
							spnr.show();
							return fm.url(file.hash, {
								async: true,
								temporary: true
							}).done(function(url) {
								_url = url;
							}).fail(function(error) {
								error && fm.error(error);
								ta.elfinderdialog('destroy');
							}).always(function() {
								spnr.hide();
							});
						}
					},
					api = function(opts) {
						$(ta).data('dfrd', url().done(function(url) {
							select.fadeOut();
							setStatus({info: 'Start conversion request.'});
							fm.request({
								data: {
									cmd: 'editor',
									name: 'OnlineConvert',
									method: 'api',
									'args[category]' : opts.category.toLowerCase(),
									'args[convert]'  : opts.convert.toLowerCase(),
									'args[options]'  : JSON.stringify(opts.options),
									'args[source]'   : fm.convAbsUrl(url),
									'args[filename]' : fm.splitFileExtention(file.name)[0] + '.' + getExt(opts.category, opts.convert),
									'args[mime]'     : file.mime
								},
								preventDefault : true
							}).done(function(data) {
								checkRes(data.apires, opts.category, opts.convert);
							}).fail(function(error) {
								error && fm.error(error);
								ta.elfinderdialog('destroy');
							});
						}));
					},
					checkRes = function(res, cat, con) {
						var status, err = [];
						if (res && res.id) {
							status = res.status;
							if (status.code === 'failed') {
								spnr.hide();
								if (res.errors && res.errors.length) {
									$.each(res.errors, function(i, o) {
										o.message && err.push(o.message);
									});
								}
								fm.error(err.length? err : status.info);
								select.fadeIn();
							} else if (status.code === 'completed') {
								upload(res.output);
							} else {
								setStatus(status);
								setTimeout(function() {
									polling(res.id);
								}, 1000);
							}
						} else {
							uiToast.appendTo(ta.closest('.ui-dialog'));
							if (res.message) {
								fm.toast({
									msg: fm.i18n(res.message),
									mode: 'error',
									timeOut: 5000,
									width: set.toastWidth,
									onHidden: function() {
										uiToast.children().length === 1 && uiToast.appendTo(fm.getUI());
									}
								});
							}
							fm.toast({
								msg: fm.i18n('editorConvNoApi'),
								mode: 'warning',
								timeOut: 3000,
								width: set.toastWidth,
								onHidden: function() {
									uiToast.children().length === 1 && uiToast.appendTo(fm.getUI());
									open(cat, con);
								}
							});
						}
					},
					setStatus = function(status) {
						spnr.show().children('.elfinder-edit-loadingmsg').text(status.info);
					},
					polling = function(jobid) {
						fm.request({
							data: {
								cmd: 'editor',
								name: 'OnlineConvert',
								method: 'api',
								'args[jobid]': jobid
							},
							preventDefault : true
						}).done(function(data) {
							checkRes(data.apires);
						}).fail(function(error) {
							error && fm.error(error);
							ta.elfinderdialog('destroy');
						});
					},
					upload = function(output) {
						var url = '';
						spnr.hide();
						if (output && output.length) {
							ta.elfinderdialog('destroy');
							$.each(output, function(i, o) {
								if (o.uri) {
									url += o.uri + '\n';
								}
							});
							fm.upload({
								target: file.phash,
								files: [url],
								type: 'text'
							});
						}
					},
					open = function(cat, con) {
						var link;
						if (cat && con) {
							if (set.conv[cat] && set.conv[cat][con] && set.conv[cat][con].link) {
								link = set.conv[cat][con].link.replace('%s', con);
							} else {
								link = cat === 'hash'? ('/' + con + '-generator') : ('/convert-to-' + con);
							}
							link = set.url.replace('%s', cat).replace('%s', link);
						} else {
							link = set.url.replace('%s', mode + '-conversion').replace('%s', '');
						}
						spnr.hide();
						select.hide();
						ifm.parent().css({overflow: fm.UA.iOS? 'auto' : 'hidden'});
						$(ta).data('dfrd', url().done(function(url) {
							var opts;
							if (url) {
								opts = {
									css: {
										height: '100%'
									}
								};
								// trigger event 'editEditorPrepare'
								ta.editor.trigger('Prepare', {
									node: ta,
									editorObj: void(0),
									instance: ifm,
									opts: opts
								});
								url = link + encodeURIComponent(fm.convAbsUrl(url));
								ifm.attr('src', url).show().css(opts.css)
									.one('load', function() {
										uiToast.appendTo(ta.closest('.ui-dialog'));
										fm.toast({
											msg: fm.i18n('editorConvNeedUpload'),
											mode: 'info',
											timeOut: 10000,
											width: set.toastWidth,
											onHidden: function() {
												uiToast.children().length === 1 && uiToast.appendTo(fm.getUI());
											},
											button: {
												text: 'btnYes'
											}
										});
									});
							} else {
								data.error && fm.error(data.error);
								ta.elfinderdialog('destroy');
							}
						}));
					},
					mode = 'document',
					cl, m;
				ifm.parent().addClass('overflow-scrolling-touch');
				if (m = file.mime.match(/^(audio|image|video)/)) {
					mode = m[1];
				}
				if (set.useTabs) {
					if (idxs[mode]) {
						btns.tabs('option', 'active', idxs[mode]);
					}
				} else {
					cl = Object.keys(set.conv).length;
					$.each(set.conv, function(t) {
						if (t.toLowerCase() === mode) {
							setOptions(t, function() {
								$.each(set.conv, function(t0) {
									t0.toLowerCase() !== mode && setOptions(t0);
								});
							});
							return false;
						}
						cl--;
					});
					if (!cl) {
						$.each(set.conv, function(t) {
							setOptions(t);
						});
					}
					ifm.parent().scrollTop(btns.children('.onlineconvert-fieldset-' + mode).offset().top);
				}
			},
			load : function() {},
			getContent : function() {},
			save : function() {},
			// Before dialog close
			beforeclose : iframeClose,
			// On dialog closed
			close : function(ta) {
				var fm = this.fm,
					dfrd = $(ta).data('dfrd');
				if (dfrd && dfrd.state() === 'pending') {
					dfrd.reject();
				}
			}
		}
	];
}, window.elFinder));
