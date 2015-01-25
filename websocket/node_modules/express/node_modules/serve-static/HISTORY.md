1.7.2 / 2015-01-02
==================

  * Fix potential open redirect when mounted at root

1.7.1 / 2014-10-22
==================

  * deps: send@0.10.1
    - deps: on-finished@~2.1.1

1.7.0 / 2014-10-15
==================

  * deps: send@0.10.0
    - deps: debug@~2.1.0
    - deps: depd@~1.0.0
    - deps: etag@~1.5.0

1.6.4 / 2014-10-08
==================

  * Fix redirect loop when index file serving disabled

1.6.3 / 2014-09-24
==================

  * deps: send@0.9.3
    - deps: etag@~1.4.0

1.6.2 / 2014-09-15
==================

  * deps: send@0.9.2
    - deps: depd@0.4.5
    - deps: etag@~1.3.1
    - deps: range-parser@~1.0.2

1.6.1 / 2014-09-07
==================

  * deps: send@0.9.1
    - deps: fresh@0.2.4

1.6.0 / 2014-09-07
==================

  * deps: send@0.9.0
    - Add `lastModified` option
    - Use `etag` to generate `ETag` header
    - deps: debug@~2.0.0

1.5.4 / 2014-09-04
==================

  * deps: send@0.8.5
    - Fix a path traversal issue when using `root`
    - Fix malicious path detection for empty string path

1.5.3 / 2014-08-17
==================

  * deps: send@0.8.3

1.5.2 / 2014-08-14
==================

  * deps: send@0.8.2
    - Work around `fd` leak in Node.js 0.10 for `fs.ReadStream`

1.5.1 / 2014-08-09
==================

  * Fix parsing of weird `req.originalUrl` values
  * deps: parseurl@~1.3.0
  * deps: utils-merge@1.0.0

1.5.0 / 2014-08-05
==================

  * deps: send@0.8.1
    - Add `extensions` option

1.4.4 / 2014-08-04
==================

  * deps: send@0.7.4
    - Fix serving index files without root dir

1.4.3 / 2014-07-29
==================

  * deps: send@0.7.3
    - Fix incorrect 403 on Windows and Node.js 0.11

1.4.2 / 2014-07-27
==================

  * deps: send@0.7.2
    - deps: depd@0.4.4

1.4.1 / 2014-07-26
==================

  * deps: send@0.7.1
    - deps: depd@0.4.3

1.4.0 / 2014-07-21
==================

  * deps: parseurl@~1.2.0
    - Cache URLs based on original value
    - Remove no-longer-needed URL mis-parse work-around
    - Simplify the "fast-path" `RegExp`
  * deps: send@0.7.0
    - Add `dotfiles` option
    - deps: debug@1.0.4
    - deps: depd@0.4.2

1.3.2 / 2014-07-11
==================

  * deps: send@0.6.0
    - Cap `maxAge` value to 1 year
    - deps: debug@1.0.3

1.3.1 / 2014-07-09
==================

  * deps: parseurl@~1.1.3
    - faster parsing of href-only URLs

1.3.0 / 2014-06-28
==================

  * Add `setHeaders` option
  * Include HTML link in redirect response
  * deps: send@0.5.0
    - Accept string for `maxAge` (converted by `ms`)

1.2.3 / 2014-06-11
==================

  * deps: send@0.4.3
    - Do not throw un-catchable error on file open race condition
    - Use `escape-html` for HTML escaping
    - deps: debug@1.0.2
    - deps: finished@1.2.2
    - deps: fresh@0.2.2

1.2.2 / 2014-06-09
==================

  * deps: send@0.4.2
    - fix "event emitter leak" warnings
    - deps: debug@1.0.1
    - deps: finished@1.2.1

1.2.1 / 2014-06-02
==================

  * use `escape-html` for escaping
  * deps: send@0.4.1
    - Send `max-age` in `Cache-Control` in correct format

1.2.0 / 2014-05-29
==================

  * deps: send@0.4.0
    - Calculate ETag with md5 for reduced collisions
    - Fix wrong behavior when index file matches directory
    - Ignore stream errors after request ends
    - Skip directories in index file search
    - deps: debug@0.8.1

1.1.0 / 2014-04-24
==================

  * Accept options directly to `send` module
  * deps: send@0.3.0

1.0.4 / 2014-04-07
==================

  * Resolve relative paths at middleware setup
  * Use parseurl to parse the URL from request

1.0.3 / 2014-03-20
==================

  * Do not rely on connect-like environments

1.0.2 / 2014-03-06
==================

  * deps: send@0.2.0

1.0.1 / 2014-03-05
==================

  * Add mime export for back-compat

1.0.0 / 2014-03-05
==================

  * Genesis from `connect`
