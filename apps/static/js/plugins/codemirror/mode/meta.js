// CodeMirror, copyright (c) by Marijn Haverbeke and others
// Distributed under an MIT license: http://codemirror.net/LICENSE

(function(mod) {
  if (typeof exports == "object" && typeof module == "object") // CommonJS
    mod(require("../lib/codemirror"));
  else if (typeof define == "function" && define.amd) // AMD
    define(["../lib/codemirror"], mod);
  else // Plain browser env
    mod(CodeMirror);
})(function(CodeMirror) {
  "use strict";

  CodeMirror.modeInfo = [
    {name: "APL", mime: "text/apl", mode: "apl", ext: ["dyalog", "apl"]},
    {name: "Asterisk", mime: "text/x-asterisk", mode: "asterisk"},
    {name: "C", mime: "text/x-csrc", mode: "clike", ext: ["c", "h"]},
    {name: "C++", mime: "text/x-c++src", mode: "clike", ext: ["cpp", "c++", "hpp", "h++"]},
    {name: "Cobol", mime: "text/x-cobol", mode: "cobol", ext: ["cob", "cpy"]},
    {name: "C#", mime: "text/x-csharp", mode: "clike", ext: ["cs"]},
    {name: "Clojure", mime: "text/x-clojure", mode: "clojure", ext: ["clj"]},
    {name: "CoffeeScript", mime: "text/x-coffeescript", mode: "coffeescript", ext: ["coffee"]},
    {name: "Common Lisp", mime: "text/x-common-lisp", mode: "commonlisp", ext: ["cl", "lisp", "el"]},
    {name: "Cypher", mime: "application/x-cypher-query", mode: "cypher"},
    {name: "Cython", mime: "text/x-cython", mode: "python", ext: ["pyx", "pxd", "pxi"]},
    {name: "CSS", mime: "text/css", mode: "css", ext: ["css"]},
    {name: "CQL", mime: "text/x-cassandra", mode: "sql", ext: ["cql"]},
    {name: "D", mime: "text/x-d", mode: "d", ext: ["d"]},
    {name: "diff", mime: "text/x-diff", mode: "diff", ext: ["diff", "patch"]},
    {name: "DTD", mime: "application/xml-dtd", mode: "dtd", ext: ["dtd"]},
    {name: "Dylan", mime: "text/x-dylan", mode: "dylan", ext: ["dylan", "dyl", "intr"]},
    {name: "ECL", mime: "text/x-ecl", mode: "ecl", ext: ["ecl"]},
    {name: "Eiffel", mime: "text/x-eiffel", mode: "eiffel", ext: ["e"]},
    {name: "Embedded Javascript", mime: "application/x-ejs", mode: "htmlembedded", ext: ["ejs"]},
    {name: "Erlang", mime: "text/x-erlang", mode: "erlang", ext: ["erl"]},
    {name: "Fortran", mime: "text/x-fortran", mode: "fortran", ext: ["f", "for", "f77", "f90"]},
    {name: "F#", mime: "text/x-fsharp", mode: "mllike", ext: ["fs"]},
    {name: "Gas", mime: "text/x-gas", mode: "gas", ext: ["s"]},
    {name: "Gherkin", mime: "text/x-feature", mode: "gherkin", ext: ["feature"]},
    {name: "GitHub Flavored Markdown", mime: "text/x-gfm", mode: "gfm"},
    {name: "Go", mime: "text/x-go", mode: "go", ext: ["go"]},
    {name: "Groovy", mime: "text/x-groovy", mode: "groovy", ext: ["groovy"]},
    {name: "HAML", mime: "text/x-haml", mode: "haml", ext: ["haml"]},
    {name: "Haskell", mime: "text/x-haskell", mode: "haskell", ext: ["hs"]},
    {name: "Haxe", mime: "text/x-haxe", mode: "haxe", ext: ["hx"]},
    {name: "HXML", mime: "text/x-hxml", mode: "haxe", ext: ["hxml"]},
    {name: "ASP.NET", mime: "application/x-aspx", mode: "htmlembedded", ext: ["aspx"]},
    {name: "HTML", mime: "text/html", mode: "htmlmixed", ext: ["html", "htm"]},
    {name: "HTTP", mime: "message/http", mode: "http"},
    {name: "Jade", mime: "text/x-jade", mode: "jade", ext: ["jade"]},
    {name: "Java", mime: "text/x-java", mode: "clike", ext: ["java"]},
    {name: "Java Server Pages", mime: "application/x-jsp", mode: "htmlembedded", ext: ["jsp"]},
    {name: "JavaScript", mimes: ["text/javascript", "text/ecmascript", "application/javascript", "application/x-javascript", "application/ecmascript"],
     mode: "javascript", ext: ["js"]},
    {name: "JSON", mimes: ["application/json", "application/x-json"], mode: "javascript", ext: ["json", "map"]},
    {name: "JSON-LD", mime: "application/ld+json", mode: "javascript"},
    {name: "Jinja2", mime: "null", mode: "jinja2"},
    {name: "Julia", mime: "text/x-julia", mode: "julia", ext: ["jl"]},
    {name: "Kotlin", mime: "text/x-kotlin", mode: "kotlin", ext: ["kt"]},
    {name: "LESS", mime: "text/x-less", mode: "css", ext: ["less"]},
    {name: "LiveScript", mime: "text/x-livescript", mode: "livescript", ext: ["ls"]},
    {name: "Lua", mime: "text/x-lua", mode: "lua", ext: ["lua"]},
    {name: "Markdown (GitHub-flavour)", mime: "text/x-markdown", mode: "markdown", ext: ["markdown", "md", "mkd"]},
    {name: "mIRC", mime: "text/mirc", mode: "mirc"},
    {name: "MariaDB SQL", mime: "text/x-mariadb", mode: "sql"},
    {name: "Modelica", mime: "text/x-modelica", mode: "modelica", ext: ["mo"]},
    {name: "MS SQL", mime: "text/x-mssql", mode: "sql"},
    {name: "MySQL", mime: "text/x-mysql", mode: "sql"},
    {name: "Nginx", mime: "text/x-nginx-conf", mode: "nginx"},
    {name: "NTriples", mime: "text/n-triples", mode: "ntriples", ext: ["nt"]},
    {name: "OCaml", mime: "text/x-ocaml", mode: "mllike", ext: ["ml", "mli", "mll", "mly"]},
    {name: "Octave", mime: "text/x-octave", mode: "octave", ext: ["m"]},
    {name: "Pascal", mime: "text/x-pascal", mode: "pascal", ext: ["p", "pas"]},
    {name: "PEG.js", mime: "null", mode: "pegjs"},
    {name: "Perl", mime: "text/x-perl", mode: "perl", ext: ["pl", "pm"]},
    {name: "PHP", mime: "application/x-httpd-php", mode: "php", ext: ["php", "php3", "php4", "php5", "phtml"]},
    {name: "Pig", mime: "text/x-pig", mode: "pig"},
    {name: "Plain Text", mime: "text/plain", mode: "null", ext: ["txt", "text", "conf", "def", "list", "log"]},
    {name: "PLSQL", mime: "text/x-plsql", mode: "sql"},
    {name: "Properties files", mime: "text/x-properties", mode: "properties", ext: ["properties", "ini", "in"]},
    {name: "Python", mime: "text/x-python", mode: "python", ext: ["py", "pyw"]},
    {name: "Puppet", mime: "text/x-puppet", mode: "puppet", ext: ["pp"]},
    {name: "Q", mime: "text/x-q", mode: "q", ext: ["q"]},
    {name: "R", mime: "text/x-rsrc", mode: "r", ext: ["r"]},
    {name: "reStructuredText", mime: "text/x-rst", mode: "rst", ext: ["rst"]},
    {name: "Ruby", mime: "text/x-ruby", mode: "ruby", ext: ["rb"]},
    {name: "Rust", mime: "text/x-rustsrc", mode: "rust", ext: ["rs"]},
    {name: "Sass", mime: "text/x-sass", mode: "sass", ext: ["sass"]},
    {name: "Scala", mime: "text/x-scala", mode: "clike", ext: ["scala"]},
    {name: "Scheme", mime: "text/x-scheme", mode: "scheme", ext: ["scm", "ss"]},
    {name: "SCSS", mime: "text/x-scss", mode: "css", ext: ["scss"]},
    {name: "Shell", mime: "text/x-sh", mode: "shell", ext: ["sh", "ksh", "bash"]},
    {name: "Sieve", mime: "application/sieve", mode: "sieve"},
    {name: "Slim", mimes: ["text/x-slim", "application/x-slim"], mode: "slim"},
    {name: "Smalltalk", mime: "text/x-stsrc", mode: "smalltalk", ext: ["st"]},
    {name: "Smarty", mime: "text/x-smarty", mode: "smarty", ext: ["tpl"]},
    {name: "SmartyMixed", mime: "text/x-smarty", mode: "smartymixed"},
    {name: "Solr", mime: "text/x-solr", mode: "solr"},
    {name: "SPARQL", mime: "application/x-sparql-query", mode: "sparql", ext: ["sparql"]},
    {name: "SQL", mime: "text/x-sql", mode: "sql", ext: ["sql"]},
    {name: "MariaDB", mime: "text/x-mariadb", mode: "sql"},
    {name: "sTeX", mime: "text/x-stex", mode: "stex"},
    {name: "LaTeX", mime: "text/x-latex", mode: "stex", ext: ["text", "ltx"]},
    {name: "SystemVerilog", mime: "text/x-systemverilog", mode: "verilog", ext: ["v"]},
    {name: "Tcl", mime: "text/x-tcl", mode: "tcl", ext: ["tcl"]},
    {name: "Textile", mime: "text/x-textile", mode: "textile"},
    {name: "TiddlyWiki ", mime: "text/x-tiddlywiki", mode: "tiddlywiki"},
    {name: "Tiki wiki", mime: "text/tiki", mode: "tiki"},
    {name: "TOML", mime: "text/x-toml", mode: "toml"},
    {name: "Tornado", mime: "text/x-tornado", mode: "tornado"},
    {name: "Turtle", mime: "text/turtle", mode: "turtle", ext: ["ttl"]},
    {name: "TypeScript", mime: "application/typescript", mode: "javascript", ext: ["ts"]},
    {name: "VB.NET", mime: "text/x-vb", mode: "vb", ext: ["vb"]},
    {name: "VBScript", mime: "text/vbscript", mode: "vbscript"},
    {name: "Velocity", mime: "text/velocity", mode: "velocity", ext: ["vtl"]},
    {name: "Verilog", mime: "text/x-verilog", mode: "verilog", ext: ["v"]},
    {name: "XML", mimes: ["application/xml", "text/xml"], mode: "xml", ext: ["xml", "xsl", "xsd"]},
    {name: "XQuery", mime: "application/xquery", mode: "xquery", ext: ["xy", "xquery"]},
    {name: "YAML", mime: "text/x-yaml", mode: "yaml", ext: ["yaml"]},
    {name: "Z80", mime: "text/x-z80", mode: "z80", ext: ["z80"]}
  ];
  // Ensure all modes have a mime property for backwards compatibility
  for (var i = 0; i < CodeMirror.modeInfo.length; i++) {
    var info = CodeMirror.modeInfo[i];
    if (info.mimes) info.mime = info.mimes[0];
  }

  CodeMirror.findModeByMIME = function(mime) {
    for (var i = 0; i < CodeMirror.modeInfo.length; i++) {
      var info = CodeMirror.modeInfo[i];
      if (info.mime == mime) return info;
      if (info.mimes) for (var j = 0; j < info.mimes.length; j++)
        if (info.mimes[j] == mime) return info;
    }
  };

  CodeMirror.findModeByExtension = function(ext) {
    for (var i = 0; i < CodeMirror.modeInfo.length; i++) {
      var info = CodeMirror.modeInfo[i];
      if (info.ext) for (var j = 0; j < info.ext.length; j++)
        if (info.ext[j] == ext) return info;
    }
  };
});
