# Contributing

As a contributor, you should agree that:

- The producer can adjust the open-source agreement to be more strict or relaxed as deemed necessary.
- Your contributed code may be used for commercial purposes, including but not limited to its cloud business operations.

## Create pull request
PR are always welcome, even if they only contain small fixes like typos or a few lines of code. If there will be a significant effort, please document it as an issue and get a discussion going before starting to work on it.

Please submit a PR broken down into small changes bit by bit. A PR consisting of a lot features and code changes may be hard to review. It is recommended to submit PRs in an incremental fashion.

This [development guideline](https://docs.jumpserver.org/zh/master/dev/rest_api/) contains information about repository structure, how to setup development environment, how to run it, and more.

Note: If you split your pull request to small changes, please make sure any of the changes goes to master will not break anything. Otherwise, it can not be merged until this feature complete.

## Report issues
It is a great way to contribute by reporting an issue. Well-written and complete bug reports are always welcome! Please open an issue and follow the template to fill in required information.

Before opening any issue, please look up the existing issues to avoid submitting a duplication.
If you find a match, you can "subscribe" to it to get notified on updates. If you have additional helpful information about the issue, please leave a comment.

When reporting issues, always include:

* Which version you are using.
* Steps to reproduce the issue.
* Snapshots or log files if needed

Because the issues are open to the public, when submitting files, be sure to remove any sensitive information, e.g. user name, password, IP address, and company name. You can
replace those parts with "REDACTED" or other strings like "****".


## Desktop client compatibility

Core represents the entire server release: Koko, Chen and Kael ship together with it.
Before changing a desktop-facing API, authentication, session, protocol or connector
contract, the developer must decide whether old clients still work and the reviewer
must check that decision. A breaking change in any server component raises
`MIN_CLIENT_VERSION` in `apps/jumpserver/settings/base.py`; ordinary compatible
releases leave it unchanged. Luna similarly maintains `MIN_CORE_VERSION`.
Both initial minimums are `v5.1.0` and both comparisons must pass before connecting.
Do not reuse an already released version number to claim the new mechanism exists.

Anonymous `GET /api/v1/settings/client/compatibility/` returns schema version 1,
the build-injected `settings.VERSION`, and `MIN_CLIENT_VERSION`, with `no-store`.
Define and inject version values with a single `v` prefix. The API returns them
unchanged, including patch, prerelease and LTS suffixes.
Keep `/api/v1/settings/client/versions/` unchanged for legacy clients. Display
versions (`CURRENT_VERSION`) and download metadata (`CLIENT_VERSION`) are not
compatibility versions. Core's development version defaults to `v5.1.0`; Luna's
package versions remain `5.1.0`. Release builds still inject their actual versions.
No per-component matrix, automatic updater or automated compatibility gate is used.

Run `python apps/manage.py test jumpserver.tests.test_client_compatibility` in the
configured development environment. Review the matching Luna desktop checks and
verify both version boundaries when changing either minimum.
