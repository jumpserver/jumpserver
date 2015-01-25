0.3.3 / 2015-01-01
==================

  * deps: debug@~2.1.1
  * deps: on-finished@~2.2.0

0.3.2 / 2014-10-22
==================

  * deps: on-finished@~2.1.1
    - Fix handling of pipelined requests

0.3.1 / 2014-10-16
==================

  * deps: debug@~2.1.0
    - Implement `DEBUG_FD` env variable support

0.3.0 / 2014-09-17
==================

  * Terminate in progress response only on error
  * Use `on-finished` to determine request status

0.2.0 / 2014-09-03
==================

  * Set `X-Content-Type-Options: nosniff` header
  * deps: debug@~2.0.0

0.1.0 / 2014-07-16
==================

  * Respond after request fully read
    - prevents hung responses and socket hang ups
  * deps: debug@1.0.4

0.0.3 / 2014-07-11
==================

  * deps: debug@1.0.3
    - Add support for multiple wildcards in namespaces

0.0.2 / 2014-06-19
==================

  * Handle invalid status codes

0.0.1 / 2014-06-05
==================

  * deps: debug@1.0.2

0.0.0 / 2014-06-05
==================

  * Extracted from connect/express
