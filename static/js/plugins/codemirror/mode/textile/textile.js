// CodeMirror, copyright (c) by Marijn Haverbeke and others
// Distributed under an MIT license: http://codemirror.net/LICENSE

(function(mod) {
  if (typeof exports == 'object' && typeof module == 'object') { // CommonJS
    mod(require('../../lib/codemirror'));
  } else if (typeof define == 'function' && define.amd) { // AMD
    define(['../../lib/codemirror'], mod);
  } else { // Plain browser env
    mod(CodeMirror);
  }
})(function(CodeMirror) {
'use strict';

var TOKEN_STYLES = {
  addition: 'positive',
  attributes: 'attribute',
  bold: 'strong',
  cite: 'keyword',
  code: 'atom',
  definitionList: 'number',
  deletion: 'negative',
  div: 'punctuation',
  em: 'em',
  footnote: 'variable',
  footCite: 'qualifier',
  header: 'header',
  html: 'comment',
  image: 'string',
  italic: 'em',
  link: 'link',
  linkDefinition: 'link',
  list1: 'variable-2',
  list2: 'variable-3',
  list3: 'keyword',
  notextile: 'string-2',
  pre: 'operator',
  p: 'property',
  quote: 'bracket',
  span: 'quote',
  specialChar: 'tag',
  strong: 'strong',
  sub: 'builtin',
  sup: 'builtin',
  table: 'variable-3',
  tableHeading: 'operator'
};

function Parser(regExpFactory, state, stream) {
  this.regExpFactory = regExpFactory;
  this.state = state;
  this.stream = stream;
  this.styles = TOKEN_STYLES;

  this.state.specialChar = null;
}

Parser.prototype.eat = function(name) {
  return this.stream.match(this.regExpFactory.pattern(name), true);
};

Parser.prototype.check = function(name) {
  return this.stream.match(this.regExpFactory.pattern(name), false);
};

Parser.prototype.setModeForNextToken = function(mode) {
  return this.state.mode = mode;
};

Parser.prototype.execMode = function(newMode) {
  return this.setModeForNextToken(newMode).call(this);
};

Parser.prototype.startNewLine = function() {
  this.setModeForNextToken(Modes.newLayout);
  this.state.tableHeading = false;

  if (this.state.layoutType === 'definitionList' && this.state.spanningLayout) {
    if (this.check('definitionListEnd')) {
      this.state.spanningLayout = false;
    }
  }
};

Parser.prototype.nextToken = function() {
  return this.state.mode.call(this);
};

Parser.prototype.styleFor = function(token) {
  if (this.styles.hasOwnProperty(token)) {
    return this.styles[token];
  }
  throw 'unknown token';
};

Parser.prototype.handlePhraseModifier = function(ch) {
  if (ch === '_') {
    if (this.stream.eat('_')) {
      return this.togglePhraseModifier('italic', /^.*__/);
    }
    return this.togglePhraseModifier('em', /^.*_/);
  }

  if (ch === '*') {
    if (this.stream.eat('*')) {
      return this.togglePhraseModifier('bold', /^.*\*\*/);
    }
    return this.togglePhraseModifier('strong', /^.*\*/);
  }

  if (ch === '[') {
    if (this.stream.match(/\d+\]/)) {
      this.state.footCite = true;
    }
    return this.tokenStyles();
  }

  if (ch === '(') {
    if (this.stream.match('r)')) {
      this.state.specialChar = 'r';
    } else if (this.stream.match('tm)')) {
      this.state.specialChar = 'tm';
    } else if (this.stream.match('c)')) {
      this.state.specialChar = 'c';
    }
    return this.tokenStyles();
  }

  if (ch === '<') {
    if (this.stream.match(/(\w+)[^>]+>[^<]+<\/\1>/)) {
      return this.tokenStylesWith(this.styleFor('html'));
    }
  }

  if (ch === '?' && this.stream.eat('?')) {
    return this.togglePhraseModifier('cite', /^.*\?\?/);
  }
  if (ch === '=' && this.stream.eat('=')) {
    return this.togglePhraseModifier('notextile', /^.*==/);
  }
  if (ch === '-') {
    return this.togglePhraseModifier('deletion', /^.*-/);
  }
  if (ch === '+') {
    return this.togglePhraseModifier('addition', /^.*\+/);
  }
  if (ch === '~') {
    return this.togglePhraseModifier('sub', /^.*~/);
  }
  if (ch === '^') {
    return this.togglePhraseModifier('sup', /^.*\^/);
  }
  if (ch === '%') {
    return this.togglePhraseModifier('span', /^.*%/);
  }
  if (ch === '@') {
    return this.togglePhraseModifier('code', /^.*@/);
  }
  if (ch === '!') {
    var type = this.togglePhraseModifier('image', /^.*(?:\([^\)]+\))?!/);
    this.stream.match(/^:\S+/); // optional Url portion
    return type;
  }
  return this.tokenStyles();
};

Parser.prototype.togglePhraseModifier = function(phraseModifier, closeRE) {
  if (this.state[phraseModifier]) { // remove phrase modifier
    var type = this.tokenStyles();
    this.state[phraseModifier] = false;
    return type;
  }
  if (this.stream.match(closeRE, false)) { // add phrase modifier
    this.state[phraseModifier] = true;
    this.setModeForNextToken(Modes.attributes);
  }
  return this.tokenStyles();
};

Parser.prototype.tokenStyles = function() {
  var disabled = this.textileDisabled(),
      styles = [];

  if (disabled) return disabled;

  if (this.state.layoutType) {
    styles.push(this.styleFor(this.state.layoutType));
  }

  styles = styles.concat(this.activeStyles('addition', 'bold', 'cite', 'code',
      'deletion', 'em', 'footCite', 'image', 'italic', 'link', 'span', 'specialChar', 'strong',
      'sub', 'sup', 'table', 'tableHeading'));

  if (this.state.layoutType === 'header') {
    styles.push(this.styleFor('header') + '-' + this.state.header);
  }
  return styles.length ? styles.join(' ') : null;
};

Parser.prototype.textileDisabled = function() {
  var type = this.state.layoutType;

  switch(type) {
    case 'notextile':
    case 'code':
    case 'pre':
      return this.styleFor(type);
    default:
      if (this.state.notextile) {
        return this.styleFor('notextile') + (type ? (' ' + this.styleFor(type)) : '');
      }

      return null;
  }
};

Parser.prototype.tokenStylesWith = function(extraStyles) {
  var disabled = this.textileDisabled(),
      type;

  if (disabled) return disabled;

  type = this.tokenStyles();
  if(extraStyles) {
    return type ? (type + ' ' + extraStyles) : extraStyles;
  }
  return type;
};

Parser.prototype.activeStyles = function() {
  var styles = [],
      i;
  for (i = 0; i < arguments.length; ++i) {
    if (this.state[arguments[i]]) {
      styles.push(this.styleFor(arguments[i]));
    }
  }
  return styles;
};

Parser.prototype.blankLine = function() {
  var spanningLayout = this.state.spanningLayout,
      type = this.state.layoutType,
      key;

  for (key in this.state) {
    if (this.state.hasOwnProperty(key)) {
      delete this.state[key];
    }
  }

  this.setModeForNextToken(Modes.newLayout);
  if (spanningLayout) {
    this.state.layoutType = type;
    this.state.spanningLayout = true;
  }
};


function RegExpFactory() {
  this.cache = {};
  this.single = {
    bc: 'bc',
    bq: 'bq',
    definitionList: /- [^(?::=)]+:=+/,
    definitionListEnd: /.*=:\s*$/,
    div: 'div',
    drawTable: /\|.*\|/,
    foot: /fn\d+/,
    header: /h[1-6]/,
    html: /\s*<(?:\/)?(\w+)(?:[^>]+)?>(?:[^<]+<\/\1>)?/,
    link: /[^"]+":\S/,
    linkDefinition: /\[[^\s\]]+\]\S+/,
    list: /(?:#+|\*+)/,
    notextile: 'notextile',
    para: 'p',
    pre: 'pre',
    table: 'table',
    tableCellAttributes: /[/\\]\d+/,
    tableHeading: /\|_\./,
    tableText: /[^"_\*\[\(\?\+~\^%@|-]+/,
    text: /[^!"_=\*\[\(<\?\+~\^%@-]+/
  };
  this.attributes = {
    align: /(?:<>|<|>|=)/,
    selector: /\([^\(][^\)]+\)/,
    lang: /\[[^\[\]]+\]/,
    pad: /(?:\(+|\)+){1,2}/,
    css: /\{[^\}]+\}/
  };
}

RegExpFactory.prototype.pattern = function(name) {
  return (this.cache[name] || this.createRe(name));
};

RegExpFactory.prototype.createRe = function(name) {
  switch (name) {
    case 'drawTable':
      return this.makeRe('^', this.single.drawTable, '$');
    case 'html':
      return this.makeRe('^', this.single.html, '(?:', this.single.html, ')*', '$');
    case 'linkDefinition':
      return this.makeRe('^', this.single.linkDefinition, '$');
    case 'listLayout':
      return this.makeRe('^', this.single.list, this.pattern('allAttributes'), '*\\s+');
    case 'tableCellAttributes':
      return this.makeRe('^', this.choiceRe(this.single.tableCellAttributes,
          this.pattern('allAttributes')), '+\\.');
    case 'type':
      return this.makeRe('^', this.pattern('allTypes'));
    case 'typeLayout':
      return this.makeRe('^', this.pattern('allTypes'), this.pattern('allAttributes'),
          '*\\.\\.?', '(\\s+|$)');
    case 'attributes':
      return this.makeRe('^', this.pattern('allAttributes'), '+');

    case 'allTypes':
      return this.choiceRe(this.single.div, this.single.foot,
          this.single.header, this.single.bc, this.single.bq,
          this.single.notextile, this.single.pre, this.single.table,
          this.single.para);

    case 'allAttributes':
      return this.choiceRe(this.attributes.selector, this.attributes.css,
          this.attributes.lang, this.attributes.align, this.attributes.pad);

    default:
      return this.makeRe('^', this.single[name]);
  }
};


RegExpFactory.prototype.makeRe = function() {
  var pattern = '',
      i,
      arg;

  for (i = 0; i < arguments.length; ++i) {
    arg = arguments[i];
    pattern += (typeof arg === 'string') ? arg : arg.source;
  }
  return new RegExp(pattern);
};

RegExpFactory.prototype.choiceRe = function() {
  var parts = [arguments[0]],
      i;

  for (i = 1; i < arguments.length; ++i) {
    parts[i * 2 - 1] = '|';
    parts[i * 2] = arguments[i];
  }

  parts.unshift('(?:');
  parts.push(')');
  return this.makeRe.apply(this, parts);
};


var Modes = {
  newLayout: function() {
    if (this.check('typeLayout')) {
      this.state.spanningLayout = false;
      return this.execMode(Modes.blockType);
    }
    if (!this.textileDisabled()) {
      if (this.check('listLayout')) {
        return this.execMode(Modes.list);
      } else if (this.check('drawTable')) {
        return this.execMode(Modes.table);
      } else if (this.check('linkDefinition')) {
        return this.execMode(Modes.linkDefinition);
      } else if (this.check('definitionList')) {
        return this.execMode(Modes.definitionList);
      } else if (this.check('html')) {
        return this.execMode(Modes.html);
      }
    }
    return this.execMode(Modes.text);
  },

  blockType: function() {
    var match,
        type;
    this.state.layoutType = null;

    if (match = this.eat('type')) {
      type = match[0];
    } else {
      return this.execMode(Modes.text);
    }

    if(match = type.match(this.regExpFactory.pattern('header'))) {
      this.state.layoutType = 'header';
      this.state.header = parseInt(match[0][1]);
    } else if (type.match(this.regExpFactory.pattern('bq'))) {
      this.state.layoutType = 'quote';
    } else if (type.match(this.regExpFactory.pattern('bc'))) {
      this.state.layoutType = 'code';
    } else if (type.match(this.regExpFactory.pattern('foot'))) {
      this.state.layoutType = 'footnote';
    } else if (type.match(this.regExpFactory.pattern('notextile'))) {
      this.state.layoutType = 'notextile';
    } else if (type.match(this.regExpFactory.pattern('pre'))) {
      this.state.layoutType = 'pre';
    } else if (type.match(this.regExpFactory.pattern('div'))) {
      this.state.layoutType = 'div';
    } else if (type.match(this.regExpFactory.pattern('table'))) {
      this.state.layoutType = 'table';
    }

    this.setModeForNextToken(Modes.attributes);
    return this.tokenStyles();
  },

  text: function() {
    if (this.eat('text')) {
      return this.tokenStyles();
    }

    var ch = this.stream.next();

    if (ch === '"') {
      return this.execMode(Modes.link);
    }
    return this.handlePhraseModifier(ch);
  },

  attributes: function() {
    this.setModeForNextToken(Modes.layoutLength);

    if (this.eat('attributes')) {
      return this.tokenStylesWith(this.styleFor('attributes'));
    }
    return this.tokenStyles();
  },

  layoutLength: function() {
    if (this.stream.eat('.') && this.stream.eat('.')) {
      this.state.spanningLayout = true;
    }

    this.setModeForNextToken(Modes.text);
    return this.tokenStyles();
  },

  list: function() {
    var match = this.eat('list'),
        listMod;
    this.state.listDepth = match[0].length;
    listMod = (this.state.listDepth - 1) % 3;
    if (!listMod) {
      this.state.layoutType = 'list1';
    } else if (listMod === 1) {
      this.state.layoutType = 'list2';
    } else {
      this.state.layoutType = 'list3';
    }
    this.setModeForNextToken(Modes.attributes);
    return this.tokenStyles();
  },

  link: function() {
    this.setModeForNextToken(Modes.text);
    if (this.eat('link')) {
      this.stream.match(/\S+/);
      return this.tokenStylesWith(this.styleFor('link'));
    }
    return this.tokenStyles();
  },

  linkDefinition: function() {
    this.stream.skipToEnd();
    return this.tokenStylesWith(this.styleFor('linkDefinition'));
  },

  definitionList: function() {
    this.eat('definitionList');

    this.state.layoutType = 'definitionList';

    if (this.stream.match(/\s*$/)) {
      this.state.spanningLayout = true;
    } else {
      this.setModeForNextToken(Modes.attributes);
    }
    return this.tokenStyles();
  },

  html: function() {
    this.stream.skipToEnd();
    return this.tokenStylesWith(this.styleFor('html'));
  },

  table: function() {
    this.state.layoutType = 'table';
    return this.execMode(Modes.tableCell);
  },

  tableCell: function() {
    if (this.eat('tableHeading')) {
      this.state.tableHeading = true;
    } else {
      this.stream.eat('|');
    }
    this.setModeForNextToken(Modes.tableCellAttributes);
    return this.tokenStyles();
  },

  tableCellAttributes: function() {
    this.setModeForNextToken(Modes.tableText);

    if (this.eat('tableCellAttributes')) {
      return this.tokenStylesWith(this.styleFor('attributes'));
    }
    return this.tokenStyles();
  },

  tableText: function() {
    if (this.eat('tableText')) {
      return this.tokenStyles();
    }

    if (this.stream.peek() === '|') { // end of cell
      this.setModeForNextToken(Modes.tableCell);
      return this.tokenStyles();
    }
    return this.handlePhraseModifier(this.stream.next());
  }
};


CodeMirror.defineMode('textile', function() {
  var regExpFactory = new RegExpFactory();

  return {
    startState: function() {
      return { mode: Modes.newLayout };
    },
    token: function(stream, state) {
      var parser = new Parser(regExpFactory, state, stream);
      if (stream.sol()) { parser.startNewLine(); }
      return parser.nextToken();
    },
    blankLine: function(state) {
      new Parser(regExpFactory, state).blankLine();
    }
  };
});

CodeMirror.defineMIME('text/x-textile', 'textile');
});
