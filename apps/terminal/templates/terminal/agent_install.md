# Connect JumpServer to your agent

Use the exact MCP URL supplied in the user's message. This guide is public and
contains no instance configuration, account information or credentials. Reading
it does not authorize asset operations. Configure only the client the user is
currently using, on the machine where that client runs. Preserve other clients
and JumpServer system settings.

## Common setup workflow

1. Identify the current agent client, its version, operating system and active
   profile from the available environment and native help. If the target cannot
   be identified, ask which client to configure; do not assume Codex or DSH.
2. Preserve unrelated settings. Reuse an existing connection to the exact URL,
   its client ID and OAuth authorization. Do not remove/re-add it to test login.
   If the existing JumpServer connection targets another URL or is disabled,
   stop and explain the conflict rather than replacing or enabling it.
3. Check that the client supports remote MCP over Streamable HTTP and native
   OAuth authorization with PKCE S256. New automatic registrations use DCR for
   public clients with no client secret and exact HTTP IP-loopback callbacks
   on `127.0.0.1` or `::1`. Cloud clients requiring HTTPS callbacks, client-secret
   authentication or CIMD-only registration cannot use this registration flow.
   Report incompatible capabilities; do not change callback or token validation.
4. Use the matching verified instructions below, or the installed client's
   native MCP commands/settings and official documentation for its version.
   Configure the supplied URL as a remote HTTP MCP connection with OAuth and
   the `agent:access` scope. Let the client handle discovery, registration, PKCE,
   token storage and refresh. Do not copy another client's commands or guess
   configuration fields. Quote arguments for the current shell.
5. Present any required authorization link to the user. The user completes
   browser login, consent and MFA; never submit them on the user's behalf.
   Never ask for passwords, MFA codes or access/refresh tokens in chat, dump
   credential files, or install by piping downloaded shell scripts into a shell.
6. Verify the live connection and tool discovery using the client's native
   status/tool list. Report saved configuration, pending authorization, reload
   required or connected according to what was actually verified. A running
   chat may need a new session before newly configured tools become available.

If the agent cannot read this guide or configure its current client, explain the
manual steps using that client's native settings: the supplied MCP URL, remote
HTTP transport, OAuth and `agent:access`, followed by browser authorization and
tool discovery. If no supported native setup path can be established, report
what is missing and stop. Do not switch to another client, invent commands or
build a replacement OAuth client. MCP asset tools operate on remote assets;
do not use them to fetch this guide or run local setup commands.

## Verified client instructions

Codex and DSH have been tested. Other clients use the common workflow above;
protocol compatibility does not by itself establish tested client support.
Follow only the instructions for the client currently being configured.

### Codex

1. Check `codex mcp --help` and `codex mcp list`. Use the server name `jumpserver`.
   Inspect only the relevant connection's URL and authentication status; do not
   print complete configuration or credential stores.
2. If it is absent, add it with `codex mcp add jumpserver --url` followed by the
   exact supplied MCP URL as one quoted argument. Do not replace an existing
   connection to a different URL.
3. Reuse working OAuth credentials. If login is needed, use
   `codex mcp login jumpserver --scopes agent:access`. Let Codex handle discovery,
   client registration, PKCE and token storage. Some versions start login during
   `mcp add`; do not start a second login while that flow is pending.
4. Present the authorization link to the user. The user must sign in and confirm
   consent on JumpServer. For a remote/headless terminal, inspect the installed
   CLI's login help for `--no-browser` support and follow its callback procedure;
   never submit a password or consent on the user's behalf.
5. Check `codex mcp list`. Reopen/reload the client if needed, then use `/mcp` to
   confirm the connection and tool discovery. A saved entry alone does not prove
   a working MCP connection. If the current chat cannot reload its tools, explain
   that a new session is needed rather than claiming the tools are already usable.

### DeepSeek Harness (DSH)

1. Use the existing `dsh-plugin-jumpserver` installation in the active DSH
   profile. Keep its fixed JumpServer name and single-connection configuration.
2. If missing, inspect `dsh plugin --help` and install the official plugin release
   package from https://github.com/LeeEirc/dsh-plugin-jumpserver/releases using
   the active profile's supported plugin command. Verify the package against its
   release SHA256SUMS. The package must contain `lib/cli.js`; if a release with
   this entry point is unavailable, stop and report that prerequisite.
3. Run `jumpserver-mcp setup --url` followed by the exact MCP URL as one quoted
   argument. If the binary is not on PATH, run `node` with the installed plugin's
   `lib/cli.js` path and the same arguments. Do not use `npx` to fetch a similarly
   named package: this plugin is distributed through GitHub Releases, not npm.
4. The command uses the plugin's existing state at `$DSH_HOME/jumpserver.json`
   (otherwise `~/.dsh/jumpserver.json`). If the running plugin has a custom
   `statePath`, pass that same path using `--state-path`; do not create a second
   state file. Existing valid tokens are reused or refreshed through the plugin.
5. If needed, keep the command running and present its browser authorization
   link to the user. The command waits for the existing PKCE loopback callback
   and verifies MCP discovery without executing tools on assets.
6. Reload the corresponding DSH profile, or reconnect through its JumpServer
   page, to load the saved connection into the host. Configuration in one host
   does not install tools on another computer or in another running profile.
7. A remote DSH host's loopback callback must be reachable from the user's
   browser through local port forwarding. If it is not, stop and explain the
   required forwarding; do not register a remote-domain callback or disable
   callback validation. Passwords and authorization remain on JumpServer.

## Completion and errors

Report configuration saved, authorization pending, reload required, or MCP
connected according to what was actually verified. Finish with connection and
tool discovery only; do not connect to assets, execute commands, or transfer files
as an installation test.

The administrator must enable MCP. New automatic registrations require DCR;
existing registered clients may reuse their authorization when DCR is off.
Each user can authorize at most ten clients. Stop on a disabled service,
registration restrictions or quota errors; do not create replacement clients or
retry unchanged failures. Users consent to their currently authorized
organizations without choosing an organization. Asset permissions, approvals
and audit permissions continue to be enforced by JumpServer.
