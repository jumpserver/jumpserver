
;(function(){

    /**
     * Require the module at `name`.
     *
     * @param {String} name
     * @return {Object} exports
     * @api public
     */

    function require(name) {
        var module = require.modules[name];
        if (!module) throw new Error('failed to require "' + name + '"');

        if (!('exports' in module) && typeof module.definition === 'function') {
            module.client = module.component = true;
            module.definition.call(this, module.exports = {}, module);
            delete module.definition;
        }

        return module.exports;
    }

    /**
     * Registered modules.
     */

    require.modules = {};

    /**
     * Register module at `name` with callback `definition`.
     *
     * @param {String} name
     * @param {Function} definition
     * @api private
     */

    require.register = function (name, definition) {
        require.modules[name] = {
            definition: definition
        };
    };

    /**
     * Define a module's exports immediately with `exports`.
     *
     * @param {String} name
     * @param {Generic} exports
     * @api private
     */

    require.define = function (name, exports) {
        require.modules[name] = {
            exports: exports
        };
    };
    require.register("component~emitter@1.1.2", function (exports, module) {

        /**
         * Expose `Emitter`.
         */

        module.exports = Emitter;

        /**
         * Initialize a new `Emitter`.
         *
         * @api public
         */

        function Emitter(obj) {
            if (obj) return mixin(obj);
        };

        /**
         * Mixin the emitter properties.
         *
         * @param {Object} obj
         * @return {Object}
         * @api private
         */

        function mixin(obj) {
            for (var key in Emitter.prototype) {
                obj[key] = Emitter.prototype[key];
            }
            return obj;
        }

        /**
         * Listen on the given `event` with `fn`.
         *
         * @param {String} event
         * @param {Function} fn
         * @return {Emitter}
         * @api public
         */

        Emitter.prototype.on =
            Emitter.prototype.addEventListener = function(event, fn){
                this._callbacks = this._callbacks || {};
                (this._callbacks[event] = this._callbacks[event] || [])
                    .push(fn);
                return this;
            };

        /**
         * Adds an `event` listener that will be invoked a single
         * time then automatically removed.
         *
         * @param {String} event
         * @param {Function} fn
         * @return {Emitter}
         * @api public
         */

        Emitter.prototype.once = function(event, fn){
            var self = this;
            this._callbacks = this._callbacks || {};

            function on() {
                self.off(event, on);
                fn.apply(this, arguments);
            }

            on.fn = fn;
            this.on(event, on);
            return this;
        };

        /**
         * Remove the given callback for `event` or all
         * registered callbacks.
         *
         * @param {String} event
         * @param {Function} fn
         * @return {Emitter}
         * @api public
         */

        Emitter.prototype.off =
            Emitter.prototype.removeListener =
                Emitter.prototype.removeAllListeners =
                    Emitter.prototype.removeEventListener = function(event, fn){
                        this._callbacks = this._callbacks || {};

                        // all
                        if (0 == arguments.length) {
                            this._callbacks = {};
                            return this;
                        }

                        // specific event
                        var callbacks = this._callbacks[event];
                        if (!callbacks) return this;

                        // remove all handlers
                        if (1 == arguments.length) {
                            delete this._callbacks[event];
                            return this;
                        }

                        // remove specific handler
                        var cb;
                        for (var i = 0; i < callbacks.length; i++) {
                            cb = callbacks[i];
                            if (cb === fn || cb.fn === fn) {
                                callbacks.splice(i, 1);
                                break;
                            }
                        }
                        return this;
                    };

        /**
         * Emit `event` with the given args.
         *
         * @param {String} event
         * @param {Mixed} ...
         * @return {Emitter}
         */

        Emitter.prototype.emit = function(event){
            this._callbacks = this._callbacks || {};
            var args = [].slice.call(arguments, 1)
                , callbacks = this._callbacks[event];

            if (callbacks) {
                callbacks = callbacks.slice(0);
                for (var i = 0, len = callbacks.length; i < len; ++i) {
                    callbacks[i].apply(this, args);
                }
            }

            return this;
        };

        /**
         * Return array of callbacks for `event`.
         *
         * @param {String} event
         * @return {Array}
         * @api public
         */

        Emitter.prototype.listeners = function(event){
            this._callbacks = this._callbacks || {};
            return this._callbacks[event] || [];
        };

        /**
         * Check if this emitter has `event` handlers.
         *
         * @param {String} event
         * @return {Boolean}
         * @api public
         */

        Emitter.prototype.hasListeners = function(event){
            return !! this.listeners(event).length;
        };

    });

    require.register("dropzone", function (exports, module) {


        /**
         * Exposing dropzone
         */
        module.exports = require("dropzone/lib/dropzone.js");

    });

    require.register("dropzone/lib/dropzone.js", function (exports, module) {

        /*
         *
         * More info at [www.dropzonejs.com](http://www.dropzonejs.com)
         *
         * Copyright (c) 2012, Matias Meno
         *
         * Permission is hereby granted, free of charge, to any person obtaining a copy
         * of this software and associated documentation files (the "Software"), to deal
         * in the Software without restriction, including without limitation the rights
         * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
         * copies of the Software, and to permit persons to whom the Software is
         * furnished to do so, subject to the following conditions:
         *
         * The above copyright notice and this permission notice shall be included in
         * all copies or substantial portions of the Software.
         *
         * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
         * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
         * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
         * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
         * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
         * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
         * THE SOFTWARE.
         *
         */

        (function() {
            var Dropzone, Em, camelize, contentLoaded, detectVerticalSquash, drawImageIOSFix, noop, without,
                __hasProp = {}.hasOwnProperty,
                __extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
                __slice = [].slice;

            Em = typeof Emitter !== "undefined" && Emitter !== null ? Emitter : require("component~emitter@1.1.2");

            noop = function() {};

            Dropzone = (function(_super) {
                var extend;

                __extends(Dropzone, _super);


                /*
                 This is a list of all available events you can register on a dropzone object.

                 You can register an event handler like this:

                 dropzone.on("dragEnter", function() { });
                 */

                Dropzone.prototype.events = ["drop", "dragstart", "dragend", "dragenter", "dragover", "dragleave", "addedfile", "removedfile", "thumbnail", "error", "errormultiple", "processing", "processingmultiple", "uploadprogress", "totaluploadprogress", "sending", "sendingmultiple", "success", "successmultiple", "canceled", "canceledmultiple", "complete", "completemultiple", "reset", "maxfilesexceeded", "maxfilesreached"];

                Dropzone.prototype.defaultOptions = {
                    url: null,
                    method: "post",
                    withCredentials: false,
                    parallelUploads: 2,
                    uploadMultiple: false,
                    maxFilesize: 256,
                    paramName: "file",
                    createImageThumbnails: true,
                    maxThumbnailFilesize: 10,
                    thumbnailWidth: 100,
                    thumbnailHeight: 100,
                    maxFiles: null,
                    params: {},
                    clickable: true,
                    ignoreHiddenFiles: true,
                    acceptedFiles: null,
                    acceptedMimeTypes: null,
                    autoProcessQueue: true,
                    autoQueue: true,
                    addRemoveLinks: false,
                    previewsContainer: null,
                    dictDefaultMessage: "Drop files here to upload",
                    dictFallbackMessage: "Your browser does not support drag'n'drop file uploads.",
                    dictFallbackText: "Please use the fallback form below to upload your files like in the olden days.",
                    dictFileTooBig: "File is too big ({{filesize}}MiB). Max filesize: {{maxFilesize}}MiB.",
                    dictInvalidFileType: "You can't upload files of this type.",
                    dictResponseError: "Server responded with {{statusCode}} code.",
                    dictCancelUpload: "Cancel upload",
                    dictCancelUploadConfirmation: "Are you sure you want to cancel this upload?",
                    dictRemoveFile: "Remove file",
                    dictRemoveFileConfirmation: null,
                    dictMaxFilesExceeded: "You can not upload any more files.",
                    accept: function(file, done) {
                        return done();
                    },
                    init: function() {
                        return noop;
                    },
                    forceFallback: false,
                    fallback: function() {
                        var child, messageElement, span, _i, _len, _ref;
                        this.element.className = "" + this.element.className + " dz-browser-not-supported";
                        _ref = this.element.getElementsByTagName("div");
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            child = _ref[_i];
                            if (/(^| )dz-message($| )/.test(child.className)) {
                                messageElement = child;
                                child.className = "dz-message";
                                continue;
                            }
                        }
                        if (!messageElement) {
                            messageElement = Dropzone.createElement("<div class=\"dz-message\"><span></span></div>");
                            this.element.appendChild(messageElement);
                        }
                        span = messageElement.getElementsByTagName("span")[0];
                        if (span) {
                            span.textContent = this.options.dictFallbackMessage;
                        }
                        return this.element.appendChild(this.getFallbackForm());
                    },
                    resize: function(file) {
                        var info, srcRatio, trgRatio;
                        info = {
                            srcX: 0,
                            srcY: 0,
                            srcWidth: file.width,
                            srcHeight: file.height
                        };
                        srcRatio = file.width / file.height;
                        trgRatio = this.options.thumbnailWidth / this.options.thumbnailHeight;
                        if (file.height < this.options.thumbnailHeight || file.width < this.options.thumbnailWidth) {
                            info.trgHeight = info.srcHeight;
                            info.trgWidth = info.srcWidth;
                        } else {
                            if (srcRatio > trgRatio) {
                                info.srcHeight = file.height;
                                info.srcWidth = info.srcHeight * trgRatio;
                            } else {
                                info.srcWidth = file.width;
                                info.srcHeight = info.srcWidth / trgRatio;
                            }
                        }
                        info.srcX = (file.width - info.srcWidth) / 2;
                        info.srcY = (file.height - info.srcHeight) / 2;
                        return info;
                    },

                    /*
                     Those functions register themselves to the events on init and handle all
                     the user interface specific stuff. Overwriting them won't break the upload
                     but can break the way it's displayed.
                     You can overwrite them if you don't like the default behavior. If you just
                     want to add an additional event handler, register it on the dropzone object
                     and don't overwrite those options.
                     */
                    drop: function(e) {
                        return this.element.classList.remove("dz-drag-hover");
                    },
                    dragstart: noop,
                    dragend: function(e) {
                        return this.element.classList.remove("dz-drag-hover");
                    },
                    dragenter: function(e) {
                        return this.element.classList.add("dz-drag-hover");
                    },
                    dragover: function(e) {
                        return this.element.classList.add("dz-drag-hover");
                    },
                    dragleave: function(e) {
                        return this.element.classList.remove("dz-drag-hover");
                    },
                    paste: noop,
                    reset: function() {
                        return this.element.classList.remove("dz-started");
                    },
                    addedfile: function(file) {
                        var node, removeFileEvent, removeLink, _i, _j, _k, _len, _len1, _len2, _ref, _ref1, _ref2, _results;
                        if (this.element === this.previewsContainer) {
                            this.element.classList.add("dz-started");
                        }
                        file.previewElement = Dropzone.createElement(this.options.previewTemplate.trim());
                        file.previewTemplate = file.previewElement;
                        this.previewsContainer.appendChild(file.previewElement);
                        _ref = file.previewElement.querySelectorAll("[data-dz-name]");
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            node = _ref[_i];
                            node.textContent = file.name;
                        }
                        _ref1 = file.previewElement.querySelectorAll("[data-dz-size]");
                        for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
                            node = _ref1[_j];
                            node.innerHTML = this.filesize(file.size);
                        }
                        if (this.options.addRemoveLinks) {
                            file._removeLink = Dropzone.createElement("<a class=\"dz-remove\" href=\"javascript:undefined;\" data-dz-remove>" + this.options.dictRemoveFile + "</a>");
                            file.previewElement.appendChild(file._removeLink);
                        }
                        removeFileEvent = (function(_this) {
                            return function(e) {
                                e.preventDefault();
                                e.stopPropagation();
                                if (file.status === Dropzone.UPLOADING) {
                                    return Dropzone.confirm(_this.options.dictCancelUploadConfirmation, function() {
                                        return _this.removeFile(file);
                                    });
                                } else {
                                    if (_this.options.dictRemoveFileConfirmation) {
                                        return Dropzone.confirm(_this.options.dictRemoveFileConfirmation, function() {
                                            return _this.removeFile(file);
                                        });
                                    } else {
                                        return _this.removeFile(file);
                                    }
                                }
                            };
                        })(this);
                        _ref2 = file.previewElement.querySelectorAll("[data-dz-remove]");
                        _results = [];
                        for (_k = 0, _len2 = _ref2.length; _k < _len2; _k++) {
                            removeLink = _ref2[_k];
                            _results.push(removeLink.addEventListener("click", removeFileEvent));
                        }
                        return _results;
                    },
                    removedfile: function(file) {
                        var _ref;
                        if ((_ref = file.previewElement) != null) {
                            _ref.parentNode.removeChild(file.previewElement);
                        }
                        return this._updateMaxFilesReachedClass();
                    },
                    thumbnail: function(file, dataUrl) {
                        var thumbnailElement, _i, _len, _ref, _results;
                        file.previewElement.classList.remove("dz-file-preview");
                        file.previewElement.classList.add("dz-image-preview");
                        _ref = file.previewElement.querySelectorAll("[data-dz-thumbnail]");
                        _results = [];
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            thumbnailElement = _ref[_i];
                            thumbnailElement.alt = file.name;
                            _results.push(thumbnailElement.src = dataUrl);
                        }
                        return _results;
                    },
                    error: function(file, message) {
                        var node, _i, _len, _ref, _results;
                        file.previewElement.classList.add("dz-error");
                        if (typeof message !== "String" && message.error) {
                            message = message.error;
                        }
                        _ref = file.previewElement.querySelectorAll("[data-dz-errormessage]");
                        _results = [];
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            node = _ref[_i];
                            _results.push(node.textContent = message);
                        }
                        return _results;
                    },
                    errormultiple: noop,
                    processing: function(file) {
                        file.previewElement.classList.add("dz-processing");
                        if (file._removeLink) {
                            return file._removeLink.textContent = this.options.dictCancelUpload;
                        }
                    },
                    processingmultiple: noop,
                    uploadprogress: function(file, progress, bytesSent) {
                        var node, _i, _len, _ref, _results;
                        _ref = file.previewElement.querySelectorAll("[data-dz-uploadprogress]");
                        _results = [];
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            node = _ref[_i];
                            _results.push(node.style.width = "" + progress + "%");
                        }
                        return _results;
                    },
                    totaluploadprogress: noop,
                    sending: noop,
                    sendingmultiple: noop,
                    success: function(file) {
                        return file.previewElement.classList.add("dz-success");
                    },
                    successmultiple: noop,
                    canceled: function(file) {
                        return this.emit("error", file, "Upload canceled.");
                    },
                    canceledmultiple: noop,
                    complete: function(file) {
                        if (file._removeLink) {
                            return file._removeLink.textContent = this.options.dictRemoveFile;
                        }
                    },
                    completemultiple: noop,
                    maxfilesexceeded: noop,
                    maxfilesreached: noop,
                    previewTemplate: "<div class=\"dz-preview dz-file-preview\">\n  <div class=\"dz-details\">\n    <div class=\"dz-filename\"><span data-dz-name></span></div>\n    <div class=\"dz-size\" data-dz-size></div>\n    <img data-dz-thumbnail />\n  </div>\n  <div class=\"dz-progress\"><span class=\"dz-upload\" data-dz-uploadprogress></span></div>\n  <div class=\"dz-success-mark\"><span>✔</span></div>\n  <div class=\"dz-error-mark\"><span>✘</span></div>\n  <div class=\"dz-error-message\"><span data-dz-errormessage></span></div>\n</div>"
                };

                extend = function() {
                    var key, object, objects, target, val, _i, _len;
                    target = arguments[0], objects = 2 <= arguments.length ? __slice.call(arguments, 1) : [];
                    for (_i = 0, _len = objects.length; _i < _len; _i++) {
                        object = objects[_i];
                        for (key in object) {
                            val = object[key];
                            target[key] = val;
                        }
                    }
                    return target;
                };

                function Dropzone(element, options) {
                    var elementOptions, fallback, _ref;
                    this.element = element;
                    this.version = Dropzone.version;
                    this.defaultOptions.previewTemplate = this.defaultOptions.previewTemplate.replace(/\n*/g, "");
                    this.clickableElements = [];
                    this.listeners = [];
                    this.files = [];
                    if (typeof this.element === "string") {
                        this.element = document.querySelector(this.element);
                    }
                    if (!(this.element && (this.element.nodeType != null))) {
                        throw new Error("Invalid dropzone element.");
                    }
                    if (this.element.dropzone) {
                        throw new Error("Dropzone already attached.");
                    }
                    Dropzone.instances.push(this);
                    this.element.dropzone = this;
                    elementOptions = (_ref = Dropzone.optionsForElement(this.element)) != null ? _ref : {};
                    this.options = extend({}, this.defaultOptions, elementOptions, options != null ? options : {});
                    if (this.options.forceFallback || !Dropzone.isBrowserSupported()) {
                        return this.options.fallback.call(this);
                    }
                    if (this.options.url == null) {
                        this.options.url = this.element.getAttribute("action");
                    }
                    if (!this.options.url) {
                        throw new Error("No URL provided.");
                    }
                    if (this.options.acceptedFiles && this.options.acceptedMimeTypes) {
                        throw new Error("You can't provide both 'acceptedFiles' and 'acceptedMimeTypes'. 'acceptedMimeTypes' is deprecated.");
                    }
                    if (this.options.acceptedMimeTypes) {
                        this.options.acceptedFiles = this.options.acceptedMimeTypes;
                        delete this.options.acceptedMimeTypes;
                    }
                    this.options.method = this.options.method.toUpperCase();
                    if ((fallback = this.getExistingFallback()) && fallback.parentNode) {
                        fallback.parentNode.removeChild(fallback);
                    }
                    if (this.options.previewsContainer) {
                        this.previewsContainer = Dropzone.getElement(this.options.previewsContainer, "previewsContainer");
                    } else {
                        this.previewsContainer = this.element;
                    }
                    if (this.options.clickable) {
                        if (this.options.clickable === true) {
                            this.clickableElements = [this.element];
                        } else {
                            this.clickableElements = Dropzone.getElements(this.options.clickable, "clickable");
                        }
                    }
                    this.init();
                }

                Dropzone.prototype.getAcceptedFiles = function() {
                    var file, _i, _len, _ref, _results;
                    _ref = this.files;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        file = _ref[_i];
                        if (file.accepted) {
                            _results.push(file);
                        }
                    }
                    return _results;
                };

                Dropzone.prototype.getRejectedFiles = function() {
                    var file, _i, _len, _ref, _results;
                    _ref = this.files;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        file = _ref[_i];
                        if (!file.accepted) {
                            _results.push(file);
                        }
                    }
                    return _results;
                };

                Dropzone.prototype.getFilesWithStatus = function(status) {
                    var file, _i, _len, _ref, _results;
                    _ref = this.files;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        file = _ref[_i];
                        if (file.status === status) {
                            _results.push(file);
                        }
                    }
                    return _results;
                };

                Dropzone.prototype.getQueuedFiles = function() {
                    return this.getFilesWithStatus(Dropzone.QUEUED);
                };

                Dropzone.prototype.getUploadingFiles = function() {
                    return this.getFilesWithStatus(Dropzone.UPLOADING);
                };

                Dropzone.prototype.getActiveFiles = function() {
                    var file, _i, _len, _ref, _results;
                    _ref = this.files;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        file = _ref[_i];
                        if (file.status === Dropzone.UPLOADING || file.status === Dropzone.QUEUED) {
                            _results.push(file);
                        }
                    }
                    return _results;
                };

                Dropzone.prototype.init = function() {
                    var eventName, noPropagation, setupHiddenFileInput, _i, _len, _ref, _ref1;
                    if (this.element.tagName === "form") {
                        this.element.setAttribute("enctype", "multipart/form-data");
                    }
                    if (this.element.classList.contains("dropzone") && !this.element.querySelector(".dz-message")) {
                        this.element.appendChild(Dropzone.createElement("<div class=\"dz-default dz-message\"><span>" + this.options.dictDefaultMessage + "</span></div>"));
                    }
                    if (this.clickableElements.length) {
                        setupHiddenFileInput = (function(_this) {
                            return function() {
                                if (_this.hiddenFileInput) {
                                    document.body.removeChild(_this.hiddenFileInput);
                                }
                                _this.hiddenFileInput = document.createElement("input");
                                _this.hiddenFileInput.setAttribute("type", "file");
                                if ((_this.options.maxFiles == null) || _this.options.maxFiles > 1) {
                                    _this.hiddenFileInput.setAttribute("multiple", "multiple");
                                }
                                _this.hiddenFileInput.className = "dz-hidden-input";
                                if (_this.options.acceptedFiles != null) {
                                    _this.hiddenFileInput.setAttribute("accept", _this.options.acceptedFiles);
                                }
                                _this.hiddenFileInput.style.visibility = "hidden";
                                _this.hiddenFileInput.style.position = "absolute";
                                _this.hiddenFileInput.style.top = "0";
                                _this.hiddenFileInput.style.left = "0";
                                _this.hiddenFileInput.style.height = "0";
                                _this.hiddenFileInput.style.width = "0";
                                document.body.appendChild(_this.hiddenFileInput);
                                return _this.hiddenFileInput.addEventListener("change", function() {
                                    var file, files, _i, _len;
                                    files = _this.hiddenFileInput.files;
                                    if (files.length) {
                                        for (_i = 0, _len = files.length; _i < _len; _i++) {
                                            file = files[_i];
                                            _this.addFile(file);
                                        }
                                    }
                                    return setupHiddenFileInput();
                                });
                            };
                        })(this);
                        setupHiddenFileInput();
                    }
                    this.URL = (_ref = window.URL) != null ? _ref : window.webkitURL;
                    _ref1 = this.events;
                    for (_i = 0, _len = _ref1.length; _i < _len; _i++) {
                        eventName = _ref1[_i];
                        this.on(eventName, this.options[eventName]);
                    }
                    this.on("uploadprogress", (function(_this) {
                        return function() {
                            return _this.updateTotalUploadProgress();
                        };
                    })(this));
                    this.on("removedfile", (function(_this) {
                        return function() {
                            return _this.updateTotalUploadProgress();
                        };
                    })(this));
                    this.on("canceled", (function(_this) {
                        return function(file) {
                            return _this.emit("complete", file);
                        };
                    })(this));
                    this.on("complete", (function(_this) {
                        return function(file) {
                            if (_this.getUploadingFiles().length === 0 && _this.getQueuedFiles().length === 0) {
                                return setTimeout((function() {
                                    return _this.emit("queuecomplete");
                                }), 0);
                            }
                        };
                    })(this));
                    noPropagation = function(e) {
                        e.stopPropagation();
                        if (e.preventDefault) {
                            return e.preventDefault();
                        } else {
                            return e.returnValue = false;
                        }
                    };
                    this.listeners = [
                        {
                            element: this.element,
                            events: {
                                "dragstart": (function(_this) {
                                    return function(e) {
                                        return _this.emit("dragstart", e);
                                    };
                                })(this),
                                "dragenter": (function(_this) {
                                    return function(e) {
                                        noPropagation(e);
                                        return _this.emit("dragenter", e);
                                    };
                                })(this),
                                "dragover": (function(_this) {
                                    return function(e) {
                                        var efct;
                                        try {
                                            efct = e.dataTransfer.effectAllowed;
                                        } catch (_error) {}
                                        e.dataTransfer.dropEffect = 'move' === efct || 'linkMove' === efct ? 'move' : 'copy';
                                        noPropagation(e);
                                        return _this.emit("dragover", e);
                                    };
                                })(this),
                                "dragleave": (function(_this) {
                                    return function(e) {
                                        return _this.emit("dragleave", e);
                                    };
                                })(this),
                                "drop": (function(_this) {
                                    return function(e) {
                                        noPropagation(e);
                                        return _this.drop(e);
                                    };
                                })(this),
                                "dragend": (function(_this) {
                                    return function(e) {
                                        return _this.emit("dragend", e);
                                    };
                                })(this)
                            }
                        }
                    ];
                    this.clickableElements.forEach((function(_this) {
                        return function(clickableElement) {
                            return _this.listeners.push({
                                element: clickableElement,
                                events: {
                                    "click": function(evt) {
                                        if ((clickableElement !== _this.element) || (evt.target === _this.element || Dropzone.elementInside(evt.target, _this.element.querySelector(".dz-message")))) {
                                            return _this.hiddenFileInput.click();
                                        }
                                    }
                                }
                            });
                        };
                    })(this));
                    this.enable();
                    return this.options.init.call(this);
                };

                Dropzone.prototype.destroy = function() {
                    var _ref;
                    this.disable();
                    this.removeAllFiles(true);
                    if ((_ref = this.hiddenFileInput) != null ? _ref.parentNode : void 0) {
                        this.hiddenFileInput.parentNode.removeChild(this.hiddenFileInput);
                        this.hiddenFileInput = null;
                    }
                    delete this.element.dropzone;
                    return Dropzone.instances.splice(Dropzone.instances.indexOf(this), 1);
                };

                Dropzone.prototype.updateTotalUploadProgress = function() {
                    var activeFiles, file, totalBytes, totalBytesSent, totalUploadProgress, _i, _len, _ref;
                    totalBytesSent = 0;
                    totalBytes = 0;
                    activeFiles = this.getActiveFiles();
                    if (activeFiles.length) {
                        _ref = this.getActiveFiles();
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            file = _ref[_i];
                            totalBytesSent += file.upload.bytesSent;
                            totalBytes += file.upload.total;
                        }
                        totalUploadProgress = 100 * totalBytesSent / totalBytes;
                    } else {
                        totalUploadProgress = 100;
                    }
                    return this.emit("totaluploadprogress", totalUploadProgress, totalBytes, totalBytesSent);
                };

                Dropzone.prototype.getFallbackForm = function() {
                    var existingFallback, fields, fieldsString, form;
                    if (existingFallback = this.getExistingFallback()) {
                        return existingFallback;
                    }
                    fieldsString = "<div class=\"dz-fallback\">";
                    if (this.options.dictFallbackText) {
                        fieldsString += "<p>" + this.options.dictFallbackText + "</p>";
                    }
                    fieldsString += "<input type=\"file\" name=\"" + this.options.paramName + (this.options.uploadMultiple ? "[]" : "") + "\" " + (this.options.uploadMultiple ? 'multiple="multiple"' : void 0) + " /><input type=\"submit\" value=\"Upload!\"></div>";
                    fields = Dropzone.createElement(fieldsString);
                    if (this.element.tagName !== "FORM") {
                        form = Dropzone.createElement("<form action=\"" + this.options.url + "\" enctype=\"multipart/form-data\" method=\"" + this.options.method + "\"></form>");
                        form.appendChild(fields);
                    } else {
                        this.element.setAttribute("enctype", "multipart/form-data");
                        this.element.setAttribute("method", this.options.method);
                    }
                    return form != null ? form : fields;
                };

                Dropzone.prototype.getExistingFallback = function() {
                    var fallback, getFallback, tagName, _i, _len, _ref;
                    getFallback = function(elements) {
                        var el, _i, _len;
                        for (_i = 0, _len = elements.length; _i < _len; _i++) {
                            el = elements[_i];
                            if (/(^| )fallback($| )/.test(el.className)) {
                                return el;
                            }
                        }
                    };
                    _ref = ["div", "form"];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        tagName = _ref[_i];
                        if (fallback = getFallback(this.element.getElementsByTagName(tagName))) {
                            return fallback;
                        }
                    }
                };

                Dropzone.prototype.setupEventListeners = function() {
                    var elementListeners, event, listener, _i, _len, _ref, _results;
                    _ref = this.listeners;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        elementListeners = _ref[_i];
                        _results.push((function() {
                            var _ref1, _results1;
                            _ref1 = elementListeners.events;
                            _results1 = [];
                            for (event in _ref1) {
                                listener = _ref1[event];
                                _results1.push(elementListeners.element.addEventListener(event, listener, false));
                            }
                            return _results1;
                        })());
                    }
                    return _results;
                };

                Dropzone.prototype.removeEventListeners = function() {
                    var elementListeners, event, listener, _i, _len, _ref, _results;
                    _ref = this.listeners;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        elementListeners = _ref[_i];
                        _results.push((function() {
                            var _ref1, _results1;
                            _ref1 = elementListeners.events;
                            _results1 = [];
                            for (event in _ref1) {
                                listener = _ref1[event];
                                _results1.push(elementListeners.element.removeEventListener(event, listener, false));
                            }
                            return _results1;
                        })());
                    }
                    return _results;
                };

                Dropzone.prototype.disable = function() {
                    var file, _i, _len, _ref, _results;
                    this.clickableElements.forEach(function(element) {
                        return element.classList.remove("dz-clickable");
                    });
                    this.removeEventListeners();
                    _ref = this.files;
                    _results = [];
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        file = _ref[_i];
                        _results.push(this.cancelUpload(file));
                    }
                    return _results;
                };

                Dropzone.prototype.enable = function() {
                    this.clickableElements.forEach(function(element) {
                        return element.classList.add("dz-clickable");
                    });
                    return this.setupEventListeners();
                };

                Dropzone.prototype.filesize = function(size) {
                    var string;
                    if (size >= 1024 * 1024 * 1024 * 1024 / 10) {
                        size = size / (1024 * 1024 * 1024 * 1024 / 10);
                        string = "TiB";
                    } else if (size >= 1024 * 1024 * 1024 / 10) {
                        size = size / (1024 * 1024 * 1024 / 10);
                        string = "GiB";
                    } else if (size >= 1024 * 1024 / 10) {
                        size = size / (1024 * 1024 / 10);
                        string = "MiB";
                    } else if (size >= 1024 / 10) {
                        size = size / (1024 / 10);
                        string = "KiB";
                    } else {
                        size = size * 10;
                        string = "b";
                    }
                    return "<strong>" + (Math.round(size) / 10) + "</strong> " + string;
                };

                Dropzone.prototype._updateMaxFilesReachedClass = function() {
                    if ((this.options.maxFiles != null) && this.getAcceptedFiles().length >= this.options.maxFiles) {
                        if (this.getAcceptedFiles().length === this.options.maxFiles) {
                            this.emit('maxfilesreached', this.files);
                        }
                        return this.element.classList.add("dz-max-files-reached");
                    } else {
                        return this.element.classList.remove("dz-max-files-reached");
                    }
                };

                Dropzone.prototype.drop = function(e) {
                    var files, items;
                    if (!e.dataTransfer) {
                        return;
                    }
                    this.emit("drop", e);
                    files = e.dataTransfer.files;
                    if (files.length) {
                        items = e.dataTransfer.items;
                        if (items && items.length && (items[0].webkitGetAsEntry != null)) {
                            this._addFilesFromItems(items);
                        } else {
                            this.handleFiles(files);
                        }
                    }
                };

                Dropzone.prototype.paste = function(e) {
                    var items, _ref;
                    if ((e != null ? (_ref = e.clipboardData) != null ? _ref.items : void 0 : void 0) == null) {
                        return;
                    }
                    this.emit("paste", e);
                    items = e.clipboardData.items;
                    if (items.length) {
                        return this._addFilesFromItems(items);
                    }
                };

                Dropzone.prototype.handleFiles = function(files) {
                    var file, _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = files.length; _i < _len; _i++) {
                        file = files[_i];
                        _results.push(this.addFile(file));
                    }
                    return _results;
                };

                Dropzone.prototype._addFilesFromItems = function(items) {
                    var entry, item, _i, _len, _results;
                    _results = [];
                    for (_i = 0, _len = items.length; _i < _len; _i++) {
                        item = items[_i];
                        if ((item.webkitGetAsEntry != null) && (entry = item.webkitGetAsEntry())) {
                            if (entry.isFile) {
                                _results.push(this.addFile(item.getAsFile()));
                            } else if (entry.isDirectory) {
                                _results.push(this._addFilesFromDirectory(entry, entry.name));
                            } else {
                                _results.push(void 0);
                            }
                        } else if (item.getAsFile != null) {
                            if ((item.kind == null) || item.kind === "file") {
                                _results.push(this.addFile(item.getAsFile()));
                            } else {
                                _results.push(void 0);
                            }
                        } else {
                            _results.push(void 0);
                        }
                    }
                    return _results;
                };

                Dropzone.prototype._addFilesFromDirectory = function(directory, path) {
                    var dirReader, entriesReader;
                    dirReader = directory.createReader();
                    entriesReader = (function(_this) {
                        return function(entries) {
                            var entry, _i, _len;
                            for (_i = 0, _len = entries.length; _i < _len; _i++) {
                                entry = entries[_i];
                                if (entry.isFile) {
                                    entry.file(function(file) {
                                        if (_this.options.ignoreHiddenFiles && file.name.substring(0, 1) === '.') {
                                            return;
                                        }
                                        file.fullPath = "" + path + "/" + file.name;
                                        return _this.addFile(file);
                                    });
                                } else if (entry.isDirectory) {
                                    _this._addFilesFromDirectory(entry, "" + path + "/" + entry.name);
                                }
                            }
                        };
                    })(this);
                    return dirReader.readEntries(entriesReader, function(error) {
                        return typeof console !== "undefined" && console !== null ? typeof console.log === "function" ? console.log(error) : void 0 : void 0;
                    });
                };

                Dropzone.prototype.accept = function(file, done) {
                    if (file.size > this.options.maxFilesize * 1024 * 1024) {
                        return done(this.options.dictFileTooBig.replace("{{filesize}}", Math.round(file.size / 1024 / 10.24) / 100).replace("{{maxFilesize}}", this.options.maxFilesize));
                    } else if (!Dropzone.isValidFile(file, this.options.acceptedFiles)) {
                        return done(this.options.dictInvalidFileType);
                    } else if ((this.options.maxFiles != null) && this.getAcceptedFiles().length >= this.options.maxFiles) {
                        done(this.options.dictMaxFilesExceeded.replace("{{maxFiles}}", this.options.maxFiles));
                        return this.emit("maxfilesexceeded", file);
                    } else {
                        return this.options.accept.call(this, file, done);
                    }
                };

                Dropzone.prototype.addFile = function(file) {
                    file.upload = {
                        progress: 0,
                        total: file.size,
                        bytesSent: 0
                    };
                    this.files.push(file);
                    file.status = Dropzone.ADDED;
                    this.emit("addedfile", file);
                    this._enqueueThumbnail(file);
                    return this.accept(file, (function(_this) {
                        return function(error) {
                            if (error) {
                                file.accepted = false;
                                _this._errorProcessing([file], error);
                            } else {
                                file.accepted = true;
                                if (_this.options.autoQueue) {
                                    _this.enqueueFile(file);
                                }
                            }
                            return _this._updateMaxFilesReachedClass();
                        };
                    })(this));
                };

                Dropzone.prototype.enqueueFiles = function(files) {
                    var file, _i, _len;
                    for (_i = 0, _len = files.length; _i < _len; _i++) {
                        file = files[_i];
                        this.enqueueFile(file);
                    }
                    return null;
                };

                Dropzone.prototype.enqueueFile = function(file) {
                    if (file.status === Dropzone.ADDED && file.accepted === true) {
                        file.status = Dropzone.QUEUED;
                        if (this.options.autoProcessQueue) {
                            return setTimeout(((function(_this) {
                                return function() {
                                    return _this.processQueue();
                                };
                            })(this)), 0);
                        }
                    } else {
                        throw new Error("This file can't be queued because it has already been processed or was rejected.");
                    }
                };

                Dropzone.prototype._thumbnailQueue = [];

                Dropzone.prototype._processingThumbnail = false;

                Dropzone.prototype._enqueueThumbnail = function(file) {
                    if (this.options.createImageThumbnails && file.type.match(/image.*/) && file.size <= this.options.maxThumbnailFilesize * 1024 * 1024) {
                        this._thumbnailQueue.push(file);
                        return setTimeout(((function(_this) {
                            return function() {
                                return _this._processThumbnailQueue();
                            };
                        })(this)), 0);
                    }
                };

                Dropzone.prototype._processThumbnailQueue = function() {
                    if (this._processingThumbnail || this._thumbnailQueue.length === 0) {
                        return;
                    }
                    this._processingThumbnail = true;
                    return this.createThumbnail(this._thumbnailQueue.shift(), (function(_this) {
                        return function() {
                            _this._processingThumbnail = false;
                            return _this._processThumbnailQueue();
                        };
                    })(this));
                };

                Dropzone.prototype.removeFile = function(file) {
                    if (file.status === Dropzone.UPLOADING) {
                        this.cancelUpload(file);
                    }
                    this.files = without(this.files, file);
                    this.emit("removedfile", file);
                    if (this.files.length === 0) {
                        return this.emit("reset");
                    }
                };

                Dropzone.prototype.removeAllFiles = function(cancelIfNecessary) {
                    var file, _i, _len, _ref;
                    if (cancelIfNecessary == null) {
                        cancelIfNecessary = false;
                    }
                    _ref = this.files.slice();
                    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                        file = _ref[_i];
                        if (file.status !== Dropzone.UPLOADING || cancelIfNecessary) {
                            this.removeFile(file);
                        }
                    }
                    return null;
                };

                Dropzone.prototype.createThumbnail = function(file, callback) {
                    var fileReader;
                    fileReader = new FileReader;
                    fileReader.onload = (function(_this) {
                        return function() {
                            var img;
                            img = document.createElement("img");
                            img.onload = function() {
                                var canvas, ctx, resizeInfo, thumbnail, _ref, _ref1, _ref2, _ref3;
                                file.width = img.width;
                                file.height = img.height;
                                resizeInfo = _this.options.resize.call(_this, file);
                                if (resizeInfo.trgWidth == null) {
                                    resizeInfo.trgWidth = _this.options.thumbnailWidth;
                                }
                                if (resizeInfo.trgHeight == null) {
                                    resizeInfo.trgHeight = _this.options.thumbnailHeight;
                                }
                                canvas = document.createElement("canvas");
                                ctx = canvas.getContext("2d");
                                canvas.width = resizeInfo.trgWidth;
                                canvas.height = resizeInfo.trgHeight;
                                drawImageIOSFix(ctx, img, (_ref = resizeInfo.srcX) != null ? _ref : 0, (_ref1 = resizeInfo.srcY) != null ? _ref1 : 0, resizeInfo.srcWidth, resizeInfo.srcHeight, (_ref2 = resizeInfo.trgX) != null ? _ref2 : 0, (_ref3 = resizeInfo.trgY) != null ? _ref3 : 0, resizeInfo.trgWidth, resizeInfo.trgHeight);
                                thumbnail = canvas.toDataURL("image/png");
                                _this.emit("thumbnail", file, thumbnail);
                                if (callback != null) {
                                    return callback();
                                }
                            };
                            return img.src = fileReader.result;
                        };
                    })(this);
                    return fileReader.readAsDataURL(file);
                };

                Dropzone.prototype.processQueue = function() {
                    var i, parallelUploads, processingLength, queuedFiles;
                    parallelUploads = this.options.parallelUploads;
                    processingLength = this.getUploadingFiles().length;
                    i = processingLength;
                    if (processingLength >= parallelUploads) {
                        return;
                    }
                    queuedFiles = this.getQueuedFiles();
                    if (!(queuedFiles.length > 0)) {
                        return;
                    }
                    if (this.options.uploadMultiple) {
                        return this.processFiles(queuedFiles.slice(0, parallelUploads - processingLength));
                    } else {
                        while (i < parallelUploads) {
                            if (!queuedFiles.length) {
                                return;
                            }
                            this.processFile(queuedFiles.shift());
                            i++;
                        }
                    }
                };

                Dropzone.prototype.processFile = function(file) {
                    return this.processFiles([file]);
                };

                Dropzone.prototype.processFiles = function(files) {
                    var file, _i, _len;
                    for (_i = 0, _len = files.length; _i < _len; _i++) {
                        file = files[_i];
                        file.processing = true;
                        file.status = Dropzone.UPLOADING;
                        this.emit("processing", file);
                    }
                    if (this.options.uploadMultiple) {
                        this.emit("processingmultiple", files);
                    }
                    return this.uploadFiles(files);
                };

                Dropzone.prototype._getFilesWithXhr = function(xhr) {
                    var file, files;
                    return files = (function() {
                        var _i, _len, _ref, _results;
                        _ref = this.files;
                        _results = [];
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            file = _ref[_i];
                            if (file.xhr === xhr) {
                                _results.push(file);
                            }
                        }
                        return _results;
                    }).call(this);
                };

                Dropzone.prototype.cancelUpload = function(file) {
                    var groupedFile, groupedFiles, _i, _j, _len, _len1, _ref;
                    if (file.status === Dropzone.UPLOADING) {
                        groupedFiles = this._getFilesWithXhr(file.xhr);
                        for (_i = 0, _len = groupedFiles.length; _i < _len; _i++) {
                            groupedFile = groupedFiles[_i];
                            groupedFile.status = Dropzone.CANCELED;
                        }
                        file.xhr.abort();
                        for (_j = 0, _len1 = groupedFiles.length; _j < _len1; _j++) {
                            groupedFile = groupedFiles[_j];
                            this.emit("canceled", groupedFile);
                        }
                        if (this.options.uploadMultiple) {
                            this.emit("canceledmultiple", groupedFiles);
                        }
                    } else if ((_ref = file.status) === Dropzone.ADDED || _ref === Dropzone.QUEUED) {
                        file.status = Dropzone.CANCELED;
                        this.emit("canceled", file);
                        if (this.options.uploadMultiple) {
                            this.emit("canceledmultiple", [file]);
                        }
                    }
                    if (this.options.autoProcessQueue) {
                        return this.processQueue();
                    }
                };

                Dropzone.prototype.uploadFile = function(file) {
                    return this.uploadFiles([file]);
                };

                Dropzone.prototype.uploadFiles = function(files) {
                    var file, formData, handleError, headerName, headerValue, headers, input, inputName, inputType, key, option, progressObj, response, updateProgress, value, xhr, _i, _j, _k, _l, _len, _len1, _len2, _len3, _len4, _m, _ref, _ref1, _ref2, _ref3, _ref4;
                    xhr = new XMLHttpRequest();
                    for (_i = 0, _len = files.length; _i < _len; _i++) {
                        file = files[_i];
                        file.xhr = xhr;
                    }
                    xhr.open(this.options.method, this.options.url, true);
                    xhr.withCredentials = !!this.options.withCredentials;
                    response = null;
                    handleError = (function(_this) {
                        return function() {
                            var _j, _len1, _results;
                            _results = [];
                            for (_j = 0, _len1 = files.length; _j < _len1; _j++) {
                                file = files[_j];
                                _results.push(_this._errorProcessing(files, response || _this.options.dictResponseError.replace("{{statusCode}}", xhr.status), xhr));
                            }
                            return _results;
                        };
                    })(this);
                    updateProgress = (function(_this) {
                        return function(e) {
                            var allFilesFinished, progress, _j, _k, _l, _len1, _len2, _len3, _results;
                            if (e != null) {
                                progress = 100 * e.loaded / e.total;
                                for (_j = 0, _len1 = files.length; _j < _len1; _j++) {
                                    file = files[_j];
                                    file.upload = {
                                        progress: progress,
                                        total: e.total,
                                        bytesSent: e.loaded
                                    };
                                }
                            } else {
                                allFilesFinished = true;
                                progress = 100;
                                for (_k = 0, _len2 = files.length; _k < _len2; _k++) {
                                    file = files[_k];
                                    if (!(file.upload.progress === 100 && file.upload.bytesSent === file.upload.total)) {
                                        allFilesFinished = false;
                                    }
                                    file.upload.progress = progress;
                                    file.upload.bytesSent = file.upload.total;
                                }
                                if (allFilesFinished) {
                                    return;
                                }
                            }
                            _results = [];
                            for (_l = 0, _len3 = files.length; _l < _len3; _l++) {
                                file = files[_l];
                                _results.push(_this.emit("uploadprogress", file, progress, file.upload.bytesSent));
                            }
                            return _results;
                        };
                    })(this);
                    xhr.onload = (function(_this) {
                        return function(e) {
                            var _ref;
                            if (files[0].status === Dropzone.CANCELED) {
                                return;
                            }
                            if (xhr.readyState !== 4) {
                                return;
                            }
                            response = xhr.responseText;
                            if (xhr.getResponseHeader("content-type") && ~xhr.getResponseHeader("content-type").indexOf("application/json")) {
                                try {
                                    response = JSON.parse(response);
                                } catch (_error) {
                                    e = _error;
                                    response = "Invalid JSON response from server.";
                                }
                            }
                            updateProgress();
                            if (!((200 <= (_ref = xhr.status) && _ref < 300))) {
                                return handleError();
                            } else {
                                return _this._finished(files, response, e);
                            }
                        };
                    })(this);
                    xhr.onerror = (function(_this) {
                        return function() {
                            if (files[0].status === Dropzone.CANCELED) {
                                return;
                            }
                            return handleError();
                        };
                    })(this);
                    progressObj = (_ref = xhr.upload) != null ? _ref : xhr;
                    progressObj.onprogress = updateProgress;
                    headers = {
                        "Accept": "application/json",
                        "Cache-Control": "no-cache",
                        "X-Requested-With": "XMLHttpRequest"
                    };
                    if (this.options.headers) {
                        extend(headers, this.options.headers);
                    }
                    for (headerName in headers) {
                        headerValue = headers[headerName];
                        xhr.setRequestHeader(headerName, headerValue);
                    }
                    formData = new FormData();
                    if (this.options.params) {
                        _ref1 = this.options.params;
                        for (key in _ref1) {
                            value = _ref1[key];
                            formData.append(key, value);
                        }
                    }
                    for (_j = 0, _len1 = files.length; _j < _len1; _j++) {
                        file = files[_j];
                        this.emit("sending", file, xhr, formData);
                    }
                    if (this.options.uploadMultiple) {
                        this.emit("sendingmultiple", files, xhr, formData);
                    }
                    if (this.element.tagName === "FORM") {
                        _ref2 = this.element.querySelectorAll("input, textarea, select, button");
                        for (_k = 0, _len2 = _ref2.length; _k < _len2; _k++) {
                            input = _ref2[_k];
                            inputName = input.getAttribute("name");
                            inputType = input.getAttribute("type");
                            if (input.tagName === "SELECT" && input.hasAttribute("multiple")) {
                                _ref3 = input.options;
                                for (_l = 0, _len3 = _ref3.length; _l < _len3; _l++) {
                                    option = _ref3[_l];
                                    if (option.selected) {
                                        formData.append(inputName, option.value);
                                    }
                                }
                            } else if (!inputType || ((_ref4 = inputType.toLowerCase()) !== "checkbox" && _ref4 !== "radio") || input.checked) {
                                formData.append(inputName, input.value);
                            }
                        }
                    }
                    for (_m = 0, _len4 = files.length; _m < _len4; _m++) {
                        file = files[_m];
                        formData.append("" + this.options.paramName + (this.options.uploadMultiple ? "[]" : ""), file, file.name);
                    }
                    return xhr.send(formData);
                };

                Dropzone.prototype._finished = function(files, responseText, e) {
                    var file, _i, _len;
                    for (_i = 0, _len = files.length; _i < _len; _i++) {
                        file = files[_i];
                        file.status = Dropzone.SUCCESS;
                        this.emit("success", file, responseText, e);
                        this.emit("complete", file);
                    }
                    if (this.options.uploadMultiple) {
                        this.emit("successmultiple", files, responseText, e);
                        this.emit("completemultiple", files);
                    }
                    if (this.options.autoProcessQueue) {
                        return this.processQueue();
                    }
                };

                Dropzone.prototype._errorProcessing = function(files, message, xhr) {
                    var file, _i, _len;
                    for (_i = 0, _len = files.length; _i < _len; _i++) {
                        file = files[_i];
                        file.status = Dropzone.ERROR;
                        this.emit("error", file, message, xhr);
                        this.emit("complete", file);
                    }
                    if (this.options.uploadMultiple) {
                        this.emit("errormultiple", files, message, xhr);
                        this.emit("completemultiple", files);
                    }
                    if (this.options.autoProcessQueue) {
                        return this.processQueue();
                    }
                };

                return Dropzone;

            })(Em);

            Dropzone.version = "3.8.7";

            Dropzone.options = {};

            Dropzone.optionsForElement = function(element) {
                if (element.getAttribute("id")) {
                    return Dropzone.options[camelize(element.getAttribute("id"))];
                } else {
                    return void 0;
                }
            };

            Dropzone.instances = [];

            Dropzone.forElement = function(element) {
                if (typeof element === "string") {
                    element = document.querySelector(element);
                }
                if ((element != null ? element.dropzone : void 0) == null) {
                    throw new Error("No Dropzone found for given element. This is probably because you're trying to access it before Dropzone had the time to initialize. Use the `init` option to setup any additional observers on your Dropzone.");
                }
                return element.dropzone;
            };

            Dropzone.autoDiscover = true;

            Dropzone.discover = function() {
                var checkElements, dropzone, dropzones, _i, _len, _results;
                if (document.querySelectorAll) {
                    dropzones = document.querySelectorAll(".dropzone");
                } else {
                    dropzones = [];
                    checkElements = function(elements) {
                        var el, _i, _len, _results;
                        _results = [];
                        for (_i = 0, _len = elements.length; _i < _len; _i++) {
                            el = elements[_i];
                            if (/(^| )dropzone($| )/.test(el.className)) {
                                _results.push(dropzones.push(el));
                            } else {
                                _results.push(void 0);
                            }
                        }
                        return _results;
                    };
                    checkElements(document.getElementsByTagName("div"));
                    checkElements(document.getElementsByTagName("form"));
                }
                _results = [];
                for (_i = 0, _len = dropzones.length; _i < _len; _i++) {
                    dropzone = dropzones[_i];
                    if (Dropzone.optionsForElement(dropzone) !== false) {
                        _results.push(new Dropzone(dropzone));
                    } else {
                        _results.push(void 0);
                    }
                }
                return _results;
            };

            Dropzone.blacklistedBrowsers = [/opera.*Macintosh.*version\/12/i];

            Dropzone.isBrowserSupported = function() {
                var capableBrowser, regex, _i, _len, _ref;
                capableBrowser = true;
                if (window.File && window.FileReader && window.FileList && window.Blob && window.FormData && document.querySelector) {
                    if (!("classList" in document.createElement("a"))) {
                        capableBrowser = false;
                    } else {
                        _ref = Dropzone.blacklistedBrowsers;
                        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                            regex = _ref[_i];
                            if (regex.test(navigator.userAgent)) {
                                capableBrowser = false;
                                continue;
                            }
                        }
                    }
                } else {
                    capableBrowser = false;
                }
                return capableBrowser;
            };

            without = function(list, rejectedItem) {
                var item, _i, _len, _results;
                _results = [];
                for (_i = 0, _len = list.length; _i < _len; _i++) {
                    item = list[_i];
                    if (item !== rejectedItem) {
                        _results.push(item);
                    }
                }
                return _results;
            };

            camelize = function(str) {
                return str.replace(/[\-_](\w)/g, function(match) {
                    return match.charAt(1).toUpperCase();
                });
            };

            Dropzone.createElement = function(string) {
                var div;
                div = document.createElement("div");
                div.innerHTML = string;
                return div.childNodes[0];
            };

            Dropzone.elementInside = function(element, container) {
                if (element === container) {
                    return true;
                }
                while (element = element.parentNode) {
                    if (element === container) {
                        return true;
                    }
                }
                return false;
            };

            Dropzone.getElement = function(el, name) {
                var element;
                if (typeof el === "string") {
                    element = document.querySelector(el);
                } else if (el.nodeType != null) {
                    element = el;
                }
                if (element == null) {
                    throw new Error("Invalid `" + name + "` option provided. Please provide a CSS selector or a plain HTML element.");
                }
                return element;
            };

            Dropzone.getElements = function(els, name) {
                var e, el, elements, _i, _j, _len, _len1, _ref;
                if (els instanceof Array) {
                    elements = [];
                    try {
                        for (_i = 0, _len = els.length; _i < _len; _i++) {
                            el = els[_i];
                            elements.push(this.getElement(el, name));
                        }
                    } catch (_error) {
                        e = _error;
                        elements = null;
                    }
                } else if (typeof els === "string") {
                    elements = [];
                    _ref = document.querySelectorAll(els);
                    for (_j = 0, _len1 = _ref.length; _j < _len1; _j++) {
                        el = _ref[_j];
                        elements.push(el);
                    }
                } else if (els.nodeType != null) {
                    elements = [els];
                }
                if (!((elements != null) && elements.length)) {
                    throw new Error("Invalid `" + name + "` option provided. Please provide a CSS selector, a plain HTML element or a list of those.");
                }
                return elements;
            };

            Dropzone.confirm = function(question, accepted, rejected) {
                if (window.confirm(question)) {
                    return accepted();
                } else if (rejected != null) {
                    return rejected();
                }
            };

            Dropzone.isValidFile = function(file, acceptedFiles) {
                var baseMimeType, mimeType, validType, _i, _len;
                if (!acceptedFiles) {
                    return true;
                }
                acceptedFiles = acceptedFiles.split(",");
                mimeType = file.type;
                baseMimeType = mimeType.replace(/\/.*$/, "");
                for (_i = 0, _len = acceptedFiles.length; _i < _len; _i++) {
                    validType = acceptedFiles[_i];
                    validType = validType.trim();
                    if (validType.charAt(0) === ".") {
                        if (file.name.toLowerCase().indexOf(validType.toLowerCase(), file.name.length - validType.length) !== -1) {
                            return true;
                        }
                    } else if (/\/\*$/.test(validType)) {
                        if (baseMimeType === validType.replace(/\/.*$/, "")) {
                            return true;
                        }
                    } else {
                        if (mimeType === validType) {
                            return true;
                        }
                    }
                }
                return false;
            };

            if (typeof jQuery !== "undefined" && jQuery !== null) {
                jQuery.fn.dropzone = function(options) {
                    return this.each(function() {
                        return new Dropzone(this, options);
                    });
                };
            }

            if (typeof module !== "undefined" && module !== null) {
                module.exports = Dropzone;
            } else {
                window.Dropzone = Dropzone;
            }

            Dropzone.ADDED = "added";

            Dropzone.QUEUED = "queued";

            Dropzone.ACCEPTED = Dropzone.QUEUED;

            Dropzone.UPLOADING = "uploading";

            Dropzone.PROCESSING = Dropzone.UPLOADING;

            Dropzone.CANCELED = "canceled";

            Dropzone.ERROR = "error";

            Dropzone.SUCCESS = "success";


            /*

             Bugfix for iOS 6 and 7
             Source: http://stackoverflow.com/questions/11929099/html5-canvas-drawimage-ratio-bug-ios
             based on the work of https://github.com/stomita/ios-imagefile-megapixel
             */

            detectVerticalSquash = function(img) {
                var alpha, canvas, ctx, data, ey, ih, iw, py, ratio, sy;
                iw = img.naturalWidth;
                ih = img.naturalHeight;
                canvas = document.createElement("canvas");
                canvas.width = 1;
                canvas.height = ih;
                ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0);
                data = ctx.getImageData(0, 0, 1, ih).data;
                sy = 0;
                ey = ih;
                py = ih;
                while (py > sy) {
                    alpha = data[(py - 1) * 4 + 3];
                    if (alpha === 0) {
                        ey = py;
                    } else {
                        sy = py;
                    }
                    py = (ey + sy) >> 1;
                }
                ratio = py / ih;
                if (ratio === 0) {
                    return 1;
                } else {
                    return ratio;
                }
            };

            drawImageIOSFix = function(ctx, img, sx, sy, sw, sh, dx, dy, dw, dh) {
                var vertSquashRatio;
                vertSquashRatio = detectVerticalSquash(img);
                return ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh / vertSquashRatio);
            };


            /*
             * contentloaded.js
             *
             * Author: Diego Perini (diego.perini at gmail.com)
             * Summary: cross-browser wrapper for DOMContentLoaded
             * Updated: 20101020
             * License: MIT
             * Version: 1.2
             *
             * URL:
             * http://javascript.nwbox.com/ContentLoaded/
             * http://javascript.nwbox.com/ContentLoaded/MIT-LICENSE
             */

            contentLoaded = function(win, fn) {
                var add, doc, done, init, poll, pre, rem, root, top;
                done = false;
                top = true;
                doc = win.document;
                root = doc.documentElement;
                add = (doc.addEventListener ? "addEventListener" : "attachEvent");
                rem = (doc.addEventListener ? "removeEventListener" : "detachEvent");
                pre = (doc.addEventListener ? "" : "on");
                init = function(e) {
                    if (e.type === "readystatechange" && doc.readyState !== "complete") {
                        return;
                    }
                    (e.type === "load" ? win : doc)[rem](pre + e.type, init, false);
                    if (!done && (done = true)) {
                        return fn.call(win, e.type || e);
                    }
                };
                poll = function() {
                    var e;
                    try {
                        root.doScroll("left");
                    } catch (_error) {
                        e = _error;
                        setTimeout(poll, 50);
                        return;
                    }
                    return init("poll");
                };
                if (doc.readyState !== "complete") {
                    if (doc.createEventObject && root.doScroll) {
                        try {
                            top = !win.frameElement;
                        } catch (_error) {}
                        if (top) {
                            poll();
                        }
                    }
                    doc[add](pre + "DOMContentLoaded", init, false);
                    doc[add](pre + "readystatechange", init, false);
                    return win[add](pre + "load", init, false);
                }
            };

            Dropzone._autoDiscoverFunction = function() {
                if (Dropzone.autoDiscover) {
                    return Dropzone.discover();
                }
            };

            contentLoaded(window, Dropzone._autoDiscoverFunction);

        }).call(this);

    });

    if (typeof exports == "object") {
        module.exports = require("dropzone");
    } else if (typeof define == "function" && define.amd) {
        define([], function(){ return require("dropzone"); });
    } else {
        this["Dropzone"] = require("dropzone");
    }
})()
