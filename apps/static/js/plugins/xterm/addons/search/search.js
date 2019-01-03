(function(f){if(typeof exports==="object"&&typeof module!=="undefined"){module.exports=f()}else if(typeof define==="function"&&define.amd){define([],f)}else{var g;if(typeof window!=="undefined"){g=window}else if(typeof global!=="undefined"){g=global}else if(typeof self!=="undefined"){g=self}else{g=this}g.search = f()}})(function(){var define,module,exports;return (function(){function r(e,n,t){function o(i,f){if(!n[i]){if(!e[i]){var c="function"==typeof require&&require;if(!f&&c)return c(i,!0);if(u)return u(i,!0);var a=new Error("Cannot find module '"+i+"'");throw a.code="MODULE_NOT_FOUND",a}var p=n[i]={exports:{}};e[i][0].call(p.exports,function(r){var n=e[i][1][r];return o(n||r)},p,p.exports,r,e,n,t)}return n[i].exports}for(var u="function"==typeof require&&require,i=0;i<t.length;i++)o(t[i]);return o}return r})()({1:[function(require,module,exports){
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var SearchHelper = (function () {
    function SearchHelper(_terminal) {
        this._terminal = _terminal;
    }
    SearchHelper.prototype.findNext = function (term) {
        if (!term || term.length === 0) {
            return false;
        }
        var result;
        var startRow = this._terminal._core.buffer.ydisp;
        if (this._terminal._core.selectionManager.selectionEnd) {
            startRow = this._terminal._core.selectionManager.selectionEnd[1];
        }
        for (var y = startRow + 1; y < this._terminal._core.buffer.ybase + this._terminal.rows; y++) {
            result = this._findInLine(term, y);
            if (result) {
                break;
            }
        }
        if (!result) {
            for (var y = 0; y < startRow; y++) {
                result = this._findInLine(term, y);
                if (result) {
                    break;
                }
            }
        }
        return this._selectResult(result);
    };
    SearchHelper.prototype.findPrevious = function (term) {
        if (!term || term.length === 0) {
            return false;
        }
        var result;
        var startRow = this._terminal._core.buffer.ydisp;
        if (this._terminal._core.selectionManager.selectionStart) {
            startRow = this._terminal._core.selectionManager.selectionStart[1];
        }
        for (var y = startRow - 1; y >= 0; y--) {
            result = this._findInLine(term, y);
            if (result) {
                break;
            }
        }
        if (!result) {
            for (var y = this._terminal._core.buffer.ybase + this._terminal.rows - 1; y > startRow; y--) {
                result = this._findInLine(term, y);
                if (result) {
                    break;
                }
            }
        }
        return this._selectResult(result);
    };
    SearchHelper.prototype._findInLine = function (term, y) {
        var lowerStringLine = this._terminal._core.buffer.translateBufferLineToString(y, true).toLowerCase();
        var lowerTerm = term.toLowerCase();
        var searchIndex = lowerStringLine.indexOf(lowerTerm);
        if (searchIndex >= 0) {
            var line = this._terminal._core.buffer.lines.get(y);
            for (var i = 0; i < searchIndex; i++) {
                var charData = line[i];
                var char = charData[1];
                if (char.length > 1) {
                    searchIndex -= char.length - 1;
                }
                var charWidth = charData[2];
                if (charWidth === 0) {
                    searchIndex++;
                }
            }
            return {
                term: term,
                col: searchIndex,
                row: y
            };
        }
    };
    SearchHelper.prototype._selectResult = function (result) {
        if (!result) {
            return false;
        }
        this._terminal._core.selectionManager.setSelection(result.col, result.row, result.term.length);
        this._terminal.scrollLines(result.row - this._terminal._core.buffer.ydisp);
        return true;
    };
    return SearchHelper;
}());
exports.SearchHelper = SearchHelper;

},{}],2:[function(require,module,exports){
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var SearchHelper_1 = require("./SearchHelper");
function findNext(terminal, term) {
    var addonTerminal = terminal;
    if (!addonTerminal.__searchHelper) {
        addonTerminal.__searchHelper = new SearchHelper_1.SearchHelper(addonTerminal);
    }
    return addonTerminal.__searchHelper.findNext(term);
}
exports.findNext = findNext;
function findPrevious(terminal, term) {
    var addonTerminal = terminal;
    if (!addonTerminal.__searchHelper) {
        addonTerminal.__searchHelper = new SearchHelper_1.SearchHelper(addonTerminal);
    }
    return addonTerminal.__searchHelper.findPrevious(term);
}
exports.findPrevious = findPrevious;
function apply(terminalConstructor) {
    terminalConstructor.prototype.findNext = function (term) {
        return findNext(this, term);
    };
    terminalConstructor.prototype.findPrevious = function (term) {
        return findPrevious(this, term);
    };
}
exports.apply = apply;

},{"./SearchHelper":1}]},{},[2])(2)
});
//# sourceMappingURL=search.js.map
