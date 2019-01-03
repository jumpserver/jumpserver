(function(f){if(typeof exports==="object"&&typeof module!=="undefined"){module.exports=f()}else if(typeof define==="function"&&define.amd){define([],f)}else{var g;if(typeof window!=="undefined"){g=window}else if(typeof global!=="undefined"){g=global}else if(typeof self!=="undefined"){g=self}else{g=this}g.zmodem = f()}})(function(){var define,module,exports;return (function(){function r(e,n,t){function o(i,f){if(!n[i]){if(!e[i]){var c="function"==typeof require&&require;if(!f&&c)return c(i,!0);if(u)return u(i,!0);var a=new Error("Cannot find module '"+i+"'");throw a.code="MODULE_NOT_FOUND",a}var p=n[i]={exports:{}};e[i][0].call(p.exports,function(r){var n=e[i][1][r];return o(n||r)},p,p.exports,r,e,n,t)}return n[i].exports}for(var u="function"==typeof require&&require,i=0;i<t.length;i++)o(t[i]);return o}return r})()({1:[function(require,module,exports){
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var zmodem;
function zmodemAttach(ws, opts) {
    if (opts === void 0) { opts = {}; }
    var term = this;
    var senderFunc = function (octets) { return ws.send(new Uint8Array(octets)); };
    var zsentry;
    function shouldWrite() {
        return !!zsentry.get_confirmed_session() || !opts.noTerminalWriteOutsideSession;
    }
    zsentry = new zmodem.Sentry({
        to_terminal: function (octets) {
            if (shouldWrite()) {
                term.write(String.fromCharCode.apply(String, octets));
            }
        },
        sender: senderFunc,
        on_retract: function () { return term.emit('zmodemRetract'); },
        on_detect: function (detection) { return term.emit('zmodemDetect', detection); }
    });
    function handleWSMessage(evt) {
        if (typeof evt.data === 'string') {
            if (shouldWrite()) {
                term.write(evt.data);
            }
        }
        else {
            zsentry.consume(evt.data);
        }
    }
    ws.binaryType = 'arraybuffer';
    ws.addEventListener('message', handleWSMessage);
}
function apply(terminalConstructor) {
    zmodem = (typeof window === 'object') ? window.Zmodem : { Browser: null };
    terminalConstructor.prototype.zmodemAttach = zmodemAttach;
    terminalConstructor.prototype.zmodemBrowser = zmodem.Browser;
}
exports.apply = apply;

},{}]},{},[1])(1)
});
//# sourceMappingURL=zmodem.js.map
