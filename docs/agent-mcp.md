# Agent MCP authorization and audit

Core provides the authorization and audit boundary for Agent asset operations.
Koko serves MCP Streamable HTTP and executes the asset protocols declared by its
execution adapters. Lina exposes system settings, personal clients and audit
tabs under session and command records. docker-web/Nginx
provides the external entry points, TLS termination and forwarding.

Clients own OAuth discovery, registration, browser login, token storage and
refresh, tool calls and result polling. Codex uses native remote MCP; a separately
developed DSH plugin can use the same contract. Core alone evaluates identity,
organization membership, current asset permissions and required approvals.
Asset credentials and internal execution capabilities are never returned to the
PC client. Koko's `docs/agent-mcp.md` covers deployment forwarding, client setup,
tools, execution semantics and file streaming.

## Configuration

Deploy the Core feature and apply normal database migrations before enabling
MCP access. The single Agent migration, `terminal.0018_agent_mcp`, creates
execution records, audit evidence and OAuth organization bindings together.

In Lina, open **System Settings > AI Assistant > MCP**. AI Assistant and MCP use
separate permission checks and save requests. Old MCP settings links redirect
to this tab. The MCP page uses
`settings.change_auth` and existing configuration-change auditing. Its API is
`/api/v1/settings/setting/?category=mcp`.

| Core setting | Meaning |
| --- | --- |
| `MCP_ENABLED` | Defaults to `false`; controls MCP access on Koko through the component configuration. Disabling stops new MCP requests after Koko synchronizes, while accepted operations and audit delivery finish |
| `MCP_PUBLIC_URL` | The exact external HTTP or HTTPS MCP URL; Core is the sole configuration source. A nonempty value must have a path, with no credentials, trailing slash, query or fragment |
| `MCP_DCR_ENABLED` | Defaults to `false`; allows controlled automatic client registration while MCP access is enabled. The preference can remain saved while MCP is disabled |
| `SITE_URL` | The existing **Basic settings > Site URL**, set to the Core address reachable by client browsers. Its HTTP or HTTPS origin, including any port, is used for Agent OAuth and is sent to Koko as `MCP_AUTHORIZATION_SERVER`; a site path is not part of the origin |

Configuration files and environment variables provide initial values. Page
settings override them through Core's normal database settings mechanism, and
Core workers receive updates through the existing settings notification path.
The URL remains editable independently of registration. Enabling MCP requires a
valid nonempty MCP URL and an HTTP or HTTPS Site URL. To clear the MCP URL,
disable MCP access in the same request or beforehand.
Valid UTF-8 percent-encoded paths retain their exact resource identity. Both Core
and Koko reject malformed escapes, decoded trailing slashes, control characters
and backslashes. Koko constructs discovery URLs with URL encoding intact.

Registered Koko components receive `MCP_ENABLED`, `MCP_PUBLIC_URL` and the derived
`MCP_AUTHORIZATION_SERVER` from
`GET /api/v1/terminal/terminals/config/`, using existing component authentication
and `terminal.view_terminalconfig`. These fields are returned independently of the
DCR preference and are not exposed to other component types. The authorization
origin is empty while disabled. Koko reads them at startup
and every 60 seconds, replacing its HTTP configuration without recreating its
execution runtime. Fetch failures, missing fields and invalid values preserve
the last valid configuration; an explicit disable stops new MCP requests.
No initial enabled configuration leaves MCP waiting. Accepted work and
audit storage remain subject to their normal authorization and lifecycle rules.

Koko needs no MCP-specific deployment settings. It retains built-in capacity
protection (128 sessions, 20 concurrent operations, 64 pending operations).
Agent OAuth metadata and Koko use the same Site URL origin; the internal
component `CORE_HOST` and incoming Host header do not select that origin.
TLS belongs to docker-web/Nginx; it may forward HTTP to Core and Koko. Clients
must support the deployment's external protocol.

MCP and file streaming use Koko's ordinary Web terminal `ClientIP()` policy,
without a separate proxy setting. In production, docker-web sanitizes forwarding
headers and backend HTTP ports remain accessible only from trusted internal
networks. Its default `USE_LB=1` overwrites client-supplied `X-Forwarded-For`;
with `USE_LB=0`, the upstream load balancer must sanitize those headers and clients
must not bypass it. Koko reports the resolved IP through component-authenticated
execution requests for the shared connection policy and audit.

Development clients may connect directly to Koko's HTTP port `5000`. Set
`MCP_PUBLIC_URL` to the client-reachable Koko URL ending in `/koko/mcp`, and set
Core's Site URL to its client-reachable login and authorization address.
No forwarding headers means the TCP peer IP is used. Keep direct access within
trusted development networks: the shared policy also parses supplied forwarding
headers. No proxy or development-mode switch is required.

The public URL is also an OAuth resource identifier. Changing it does not rebind
issued credentials or sessions. Finish important sessions, disable MCP, update
the URL and proxy forwarding, then re-enable MCP and confirm Koko's resource
metadata. Clients then update their URL and register/authorize again. New
clients cannot take over another client's sessions. Polling is not an atomic
rollout or a one-minute guarantee during outages.

## Client registration and authorization

The public authorization-server metadata is at
`/.well-known/oauth-authorization-server`. Proxies route it and the existing
`/core/auth/oauth2-provider/` endpoints to Core. Koko's protected-resource metadata
identifies the Core authorization server. Discovery responses are not cached.

Core advertises `registration_endpoint` only when MCP and DCR are enabled. Registration
creates a public authorization-code client with no client secret and binds it to
Core's configured MCP resource. The registration body and Host header cannot
select that resource. Registration alone grants no asset access.

The registration profile accepts only literal `127.0.0.1` or `::1` HTTP loopback
callbacks. The registered path and query remain fixed while the local callback
port may vary. The browser redirect permits HTTP only for an active Agent
registration's validated callback; the redirect policies of other OAuth clients
are unchanged. CIMD and dynamic client management are not enabled.

Registration accepts at most 8 KiB of JSON and four callback URIs. Shared limits
allow 30 attempts per minute and 4,096 dynamic Agent clients per deployment.
Redis coordination failures reject registration. Clients persist and reuse the
issued client ID.

Each authorization uses:

- `agent:access` scope and the exact MCP `resource` indicator;
- authorization code with PKCE S256;
- browser login and explicit consent covering the user's available organizations;
- public-client token and revocation requests without a client secret.

Consent is required on each authorization, without an organization selector.
Grants cover the signed-in user's currently available organizations,
excluding global/system organizations. Each request rechecks membership and
asset, account and protocol permissions; the all-organizations marker grants no
administrative authority. Connections resolve the actual organization from the
authorized asset. Clients need not send `X-JMS-ORG`, and a header cannot expand
the grant. Agent access tokens are rejected as ordinary Core API bearer credentials.

## Revocation and registration maintenance

Disabling DCR stops new registrations and removes registration discovery. It does
not revoke existing grants or stop the MCP service. Clients can revoke tokens
through the advertised OAuth revocation endpoint. In **Personal Settings >
Agent / MCP**, users see their own clients and connection documentation, across
all their organizations. Each user can authorize at most ten distinct clients;
the same client in several organizations counts once. Existing disabled
registrations still cannot authorize or execute.

The personal API is `/api/v1/authentication/user-agent-clients/`: GET lists the
current user's clients; POST `{id}/revoke/` revokes that user's authorization in
all organizations. Other users' grants are preserved. When no authorization
remains, the unused Agent registration is reclaimed automatically. Referenced
OAuth identities and execution history are retained; an unreferenced identity
can be removed. Revocation records an operation audit with operator, source IP,
client and result. It never lets an ordinary user re-enable a disabled client.

Administrators manage system configuration only. User management and settings
do not expose personal client lists or client operations; the former
`agent-clients/` and `agent-client-authorizations/` management APIs are absent.
Koko rechecks idle sessions too, including database connections with open
transactions. Its maintenance loop starts batches at least five seconds apart,
checks up to 16 sessions with one-second request and five-second batch budgets,
and closes connections on explicit authorization denial or missing sessions.
Transient service failures are retried; new dispatch still requires Core.
Batching and network delays mean this is not a five-second node-wide guarantee.

The existing scheduled OAuth token cleanup removes bounded batches of
never-authorized dynamic registrations older than seven days, considering at
most 100 eligible clients per run and recording its summary in task logs.
Related grants, tokens, sessions or audit records prevent deletion; references
are rechecked under the authorization lock order. No manual cleanup API, extra
deployment schedule or management command is needed. Registration coordination
failures leave records for a later attempt.

## Component authorization boundary

The component-operation routes below share the prefix
`/api/v1/terminal/agent/`. They require a registered, active Koko service account
with `authentication.add_superconnectiontoken`, using component authentication
rather than client OAuth bearer authentication. The audit routes described below
use their separate user and auditor permissions.

| Component operation | Contract |
| --- | --- |
| `introspect/` | Validates the external OAuth token, exact resource, all-organization scope and required versioned node capabilities; returns a context bound to these values and the user, client and Koko node for at most five minutes |
| `assets/` | Searches current authorized assets, accounts and supported protocols using that context |
| `sessions/` | Creates an idempotent logical asset session and connection action; applies existing connection controls |
| `sessions/list/`, `sessions/get/` | Lists or recovers public session metadata by ID or original connection key; never returns credentials or restores a transport |
| `sessions/<id>/credentials/` | Releases connection credentials to the bound Koko node once, after authorization |
| `sessions/<id>/check/`, `bind/`, `close/` | Revalidates authority, binds the real terminal session, or closes the logical session after dispatched work drains |
| `actions/` | Registers an immutable operation and its request hash |
| `actions/list/`, `actions/lookup/` | Finds operation IDs and states in the current user's client, node and currently authorized organizations |
| `actions/<id>/authorize/`, `claim/` | Rechecks current authority and approvals, then grants dispatch once |
| `actions/<id>/get/`, `cancel/` | Queries or cancels actions belonging to the authenticated user, client and organization |
| `actions/<id>/events/` | Accepts ordered execution evidence from the bound node |

Session capabilities bind the node and durable session; they never carry asset
credentials. Each new operation rechecks the grant, user, organization,
connection controls and asset permissions. Normal token rotation preserves the
grant family. Revocation, removal of the user or permissions, or a disabled
registration prevents further dispatch. Without a refresh family, the original
access token must remain unexpired.

Asset discovery supports `asset_id` within the authorized asset set and optional
`account_offset` (0–100,000). Each asset returns at most 100 accounts with
`accounts_next_offset`; real account rows are paged before permission expansion.

Recovery lists use bounded offset pages of at most 100 rows and an optional
status filter; action lists also accept a session filter. Session recovery
accepts exactly one session ID or original connection key. Action lookup takes
the original operation key and an optional session filter; known action IDs use
the existing action get endpoint. Ambiguous keys across organizations require
an ID (or an action's session filter). Queries cannot
select another user, client, node or arbitrary organization. Current session
capability hints contain permitted action effects, execution mode and whether
command context needs review; dispatch still rechecks authority and approvals.
Expired sessions remain historical records and cannot restore a native connection.

Component validation errors include a stable `code` with their existing detail.
Koko translates recognized public codes without exposing arbitrary Core error
bodies or credential details. This error presentation is confined to Agent
component endpoints; ordinary Core APIs retain their existing contract.

### MCP tool boundary

Koko exposes ten MCP tools. Core component routes and action kinds express
stable authorization effects rather than duplicating the public tool catalog:

| Koko MCP tool | Core route or action |
| --- | --- |
| `search_assets` | `assets/` |
| `connect_asset` | `sessions/` |
| `query_sessions` | `operation=get/list` uses `sessions/get/` or `sessions/list/` |
| `disconnect_asset` | `sessions/<id>/close/` |
| `execute_command` | Action kind `execute_command` |
| `query_actions` | `operation=get` uses action get or lookup; `operation=list` uses `actions/list/` |
| `cancel_action` | `actions/<id>/cancel/` |
| `file_read` | `operation=list/stat/read/download` maps to `file_list/file_stat/file_read/file_download` |
| `file_write` | `operation=write/upload/mkdir/rename/remove` maps to `file_write/file_upload/file_mkdir/file_rename/file_remove` |
| `open_terminal` | Action kind `open_terminal` |

Each file action retains its own connect, download, upload or delete permission
and audit kind. Component introspection accepts the resource, token and node
capability declaration; client-selected organization fields are rejected.

### Execution capabilities and extension

Koko supplies `capabilities` during component-authenticated introspection:
version `1` and a `protocols` mapping from adapter names to `shell`, `database`
or `files`. Declarations allow 1–32 protocol names of at most 16 characters;
unknown versions, modes and malformed names are rejected. MCP clients cannot
supply this declaration. Core signs it into the node-bound context and returns
only protocols in both the declaration and current asset/account permissions.

Session creation applies the same intersection and stores the derived execution
mode in the existing request JSON. Refreshing capabilities cannot reinterpret
an existing session or reuse its idempotency key with another mode. Capability
declarations and stored execution modes are required; missing or unsupported
values are rejected. Core contains no protocol-driver fallback list.

Koko owns tool names, tool-specific schemas and execution adapters. Core owns
stable action policies: permitted execution modes, authorization-relevant
fields, connect/upload/download/delete permissions, approvals, request binding
and audit. A new driver for an already supported asset protocol or a new tool
using an existing action needs no Core adapter-list change. A new security
effect requires an explicit Core policy; node declarations cannot invent
permissions or bypass connection controls. Unknown actions remain rejected.

## Approval and human interaction

Session and action idempotency keys are unique per organization, user and client.
Reusing a key with different parameters is rejected. Core claims an action
atomically once. Command approval tickets contain the immutable request and its
SHA256 and bind the original action, terminal session and current ACL. Changes
to the ticket or policy invalidate an outstanding approval. SSH commands have a
4,096-character limit; working directory and environment are explicit fields.
Agents do not send raw interactive terminal input through these APIs.

When command filters apply, a nonempty working directory or environment cannot
be authorized from the command text alone. Such a request must match a review
rule and pass the existing full-request approval. Automatic accept, warning and
unmatched paths reject contextual requests with a controlled-terminal handoff
hint. This is checked again at dispatch claim, including previously queued work.
Context-free commands retain normal command filtering; sessions without command
filters still support explicit context. Rejected actions and their original
requests remain auditable.

The `warning` command policy permits execution while retaining the matched rule
and risk in the action audit and using the existing warning notification flow.
The `notify_and_warn` policy requires interactive confirmation: native execution
is rejected with instructions to use `open_terminal`, whose existing terminal
flow collects that confirmation. Cancelling or terminating a pending action also
closes its pending approval. Shared connection review tickets remain open while
another connection still needs them.

The logged-in owner completes personal credentials, reason, MFA, face and review
steps at `/core/auth/agent/session/<id>/`. Credentials stay in Core. A policy
requiring live face monitoring yields `requires_terminal` instead of starting an
unattended connection.

`open_terminal` creates an `awaiting_input` action and a human handoff URL. The
owner starts a separate, one-time connection through the existing Luna/Koko
terminal flow. Only creation of the actual terminal session completes the
handoff; subsequent input uses existing ACL filtering, audit and recording. It
shares no Shell context with independent Agent commands.

Handoff remains available after automatic connection failure while the logical
session and grant are valid. It rechecks current asset/account/protocol
permission and uses a fresh token with normal connection ACLs. Closed, expired
or revoked sessions cannot be reopened. Both Agent handoff and the web API use
`ConnectionTokenService` for token creation and ACL initialization.

For live-monitor policies, the page retains the Luna camera monitor and loads the
terminal only after monitoring starts. Monitor errors close the embedded
terminal. The page and camera stay open; the existing monitor service manages
pause, resume and termination.

## Audit, limits and recovery

Audit pages are `/core/auth/agent/audit/sessions/` and
`/core/auth/agent/audit/actions/`; JSON routes are under
`/api/v1/terminal/agent/audit/`. Owners can inspect their own records, and existing
organization/system auditors receive the new view permissions. Evidence-detail
reads generate operation logs. Lists and session action histories use bounded
100-row offset pages; event pages use immutable sequence cursors. Responses
include the terminal session, request hash and approval ticket.
Audit links and page navigation carry `oid` for the record's organization, so
selecting an OAuth organization different from the browser's current organization
does not break authorized audit access. The parameter does not grant permission.

Each event has a UUID and a strictly increasing per-action sequence. Exact
retries are acknowledged; changed evidence, gaps and active-state regressions
are rejected. Late observations remain in the record without replacing a
terminal status or result. The bound component can deliver late evidence after
OAuth expiry/revocation or session closure. Koko retains its encrypted outbox
until Core acknowledges delivery.
Koko also budgets encoded evidence before persistence and reserves space for the
terminal event. Delivery rotates between actions while preserving each action's
event order; one persistently rejected action cannot block unrelated evidence.

Closing a session cancels unclaimed and pending human operations and refuses
closure while dispatched operations are running. Cancellation of running work
requires confirmed remote termination; otherwise the result remains uncertain.
When recovery cannot establish whether Core received a claim, an `unknown`
receipt can also terminate an unclaimed action. Repeating that receipt is
idempotent and prevents later dispatch of the action.
Native session closure uses the existing terminal-session update flow, including
configured end-of-session credential rotation. Repeated closure does not repeat
that transition.

Limits include 16 live sessions per user in an organization, a two-hour session lifetime, 32 pending
actions per session, 64 KiB requests (512 KiB encoded JSON for `file_write`, whose
UTF-8 content is separately limited to 64 KiB), 128 KiB events and 16 MiB evidence per action,
with space reserved for final evidence. Command approval validity is 15 minutes.
The single-node release does not fail over uncertain actions to another worker.

Normal retention and encrypted-backup policies must cover Agent audit tables.
Connection credential records use the existing token retention task. Active
Agent connections are excluded from early cleanup until their bounded session
expires or closes; audit records retain the immutable requested
asset/account/protocol after the credential record is removed.

## Validation

Run the relevant tests with an isolated PostgreSQL database and Redis and bounded
parallelism:

```sh
python apps/manage.py test terminal.test_agent terminal.test_agent_oauth authentication.tests.test_agent_registration settings.test_mcp_settings --parallel 1
python apps/manage.py check
python apps/manage.py makemigrations --check --dry-run
```

These checks cover Core's execution, organization-bound OAuth, registration and
settings contracts. Deployment acceptance separately exercises browser login,
multi-organization authorization, asset authorization, approvals, handoff, audit access and
reverse-proxy behavior against isolated assets.
