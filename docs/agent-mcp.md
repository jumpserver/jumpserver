# Agent MCP authorization and audit

Core provides the authorization and audit boundary for Agent asset operations.
Koko serves MCP Streamable HTTP and executes SSH, SFTP, MySQL/MariaDB and
PostgreSQL operations. Lina exposes the Core settings page. docker-web/Nginx
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
MCP access. The initial Agent migration creates execution records, audit evidence
and OAuth organization bindings together.

In Lina, open **System Settings > Feature Settings > Agent / MCP**. The page uses
`settings.change_auth` and existing configuration-change auditing. Its API is
`/api/v1/settings/setting/?category=mcp`.

| Core setting | Meaning |
| --- | --- |
| `MCP_PUBLIC_URL` | The exact external HTTP or HTTPS MCP URL; Core is the sole configuration source. A nonempty value must have a path, with no credentials, trailing slash, query or fragment |
| `MCP_DCR_ENABLED` | Defaults to `false`; enables controlled automatic client registration. A valid nonempty MCP URL is required when enabled |

Configuration files and environment variables provide initial values. Page
settings override them through Core's normal database settings mechanism, and
Core workers receive updates through the existing settings notification path.
The URL remains editable independently of registration. To clear it, disable
automatic registration in the same request or beforehand.
Valid UTF-8 percent-encoded paths retain their exact resource identity. Both Core
and Koko reject malformed escapes, decoded trailing slashes, control characters
and backslashes. Koko constructs discovery URLs with URL encoding intact.

Registered Koko components receive `MCP_PUBLIC_URL` from
`GET /api/v1/terminal/terminals/config/`, using existing component authentication
and `terminal.view_terminalconfig`. The field is returned independently of the
DCR switch and is not exposed to other component types. Koko reads it at startup
and every 60 seconds, replacing its HTTP configuration without recreating its
execution runtime. Fetch failures, missing fields and invalid values preserve
the last valid configuration; an explicitly empty value stops new MCP requests.
No initial valid address leaves MCP waiting for configuration. Accepted work and
audit storage remain subject to their normal authorization and lifecycle rules.

Koko's enablement, public authorization-server origin and execution limits remain
Koko deployment settings. TLS belongs to docker-web/Nginx; it may forward HTTP to
Core and Koko. Preserve the external Host and `X-Forwarded-Proto` so Core publishes
the correct OAuth issuer and endpoints. Clients must support the deployment's
external protocol.

MCP and file streaming use Koko's ordinary Web terminal `ClientIP()` policy,
without a separate proxy setting. In production, docker-web sanitizes forwarding
headers and backend HTTP ports remain accessible only from trusted internal
networks. Its default `USE_LB=1` overwrites client-supplied `X-Forwarded-For`;
with `USE_LB=0`, the upstream load balancer must sanitize those headers and clients
must not bypass it. Koko reports the resolved IP through component-authenticated
execution requests for the shared connection policy and audit.

Development clients may connect directly to Koko's HTTP port `5000`. Set
`MCP_PUBLIC_URL` to the client-reachable Koko URL ending in `/koko/mcp`, while
`MCP_AUTHORIZATION_SERVER` still points to Core's login and authorization origin.
No forwarding headers means the TCP peer IP is used. Keep direct access within
trusted development networks: the shared policy also parses supplied forwarding
headers. No proxy or development-mode switch is required.

The public URL is also an OAuth resource identifier. Changing it does not rebind
issued credentials or sessions. Finish important sessions, disable DCR, update
the URL and proxy forwarding, and confirm Koko's resource metadata before
re-enabling DCR. Clients then update their URL and register/authorize again. New
clients cannot take over another client's sessions. Polling is not an atomic
rollout or a one-minute guarantee during outages.

## Client registration and authorization

The public authorization-server metadata is at
`/.well-known/oauth-authorization-server`. Proxies route it and the existing
`/core/auth/oauth2-provider/` endpoints to Core. Koko's protected-resource metadata
identifies the Core authorization server. Discovery responses are not cached.

Core advertises `registration_endpoint` only when DCR is enabled. Registration
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
- browser login, explicit consent and a choice of organization;
- public-client token and revocation requests without a client secret.

Consent is required on each authorization. The page lists only organizations
available to the signed-in user and excludes global/system organizations. A
single organization can be selected automatically; multiple organizations
require an explicit choice. Every Agent grant, access token and refresh flow
requires a valid organization binding. The choice is attached to the individual
authorization and token family, not a mutable default for the user or client.

Introspection obtains the organization from that binding. Clients need not send
`X-JMS-ORG`; a conflicting header is rejected. Switching organizations requires
fresh authorization. Refresh preserves the organization and rechecks membership.
Agent access tokens are rejected as ordinary Core API bearer credentials.

## Revocation and registration maintenance

Disabling DCR stops new registrations and removes registration discovery. It does
not revoke existing grants or stop the MCP service. Clients revoke their grants
through the advertised OAuth revocation endpoint. Administrators can disable an
Agent client using `python apps/manage.py disable_agent_oauth_client --client-id <CLIENT_ID>`.
Disabled registrations cannot authorize further execution. This control is
separate from cancelling an action or closing an asset session.
Koko rechecks idle sessions too, including database connections with open
transactions. Its maintenance loop starts batches at least five seconds apart,
checks up to 16 sessions with one-second request and five-second batch budgets,
and closes connections on explicit authorization denial or missing sessions.
Transient service failures are retried; new dispatch still requires Core.
Batching and network delays mean this is not a five-second node-wide guarantee.

Run `python apps/manage.py cleanup_agent_oauth_clients` to remove a bounded batch
of never-authorized dynamic registrations. Defaults are at most 100 candidates
older than seven days. Related grants, tokens, sessions or audit records prevent
deletion. Authorized clients and execution history are retained. Scheduling this
maintenance is a deployment responsibility.

## Component authorization boundary

The component-operation routes below share the prefix
`/api/v1/terminal/agent/`. They require a registered, active Koko service account
with `authentication.add_superconnectiontoken`, using component authentication
rather than client OAuth bearer authentication. The audit routes described below
use their separate user and auditor permissions.

| Component operation | Contract |
| --- | --- |
| `introspect/` | Validates the external OAuth token, exact resource and organization binding; returns a context bound to user, client, organization, resource and Koko node for at most five minutes |
| `assets/` | Searches current authorized assets, accounts and supported protocols using that context |
| `sessions/` | Creates an idempotent logical asset session and connection action; applies existing connection controls |
| `sessions/<id>/credentials/` | Releases connection credentials to the bound Koko node once, after authorization |
| `sessions/<id>/check/`, `bind/`, `close/` | Revalidates authority, binds the real terminal session, or closes the logical session after dispatched work drains |
| `actions/` | Registers an immutable operation and its request hash |
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

## Approval and human interaction

Session and action idempotency keys are unique per organization, user and client.
Reusing a key with different parameters is rejected. Core claims an action
atomically once. Command approval tickets contain the immutable request and its
SHA256 and bind the original action, terminal session and current ACL. Changes
to the ticket or policy invalidate an outstanding approval. SSH commands have a
4,096-character limit; working directory and environment are explicit fields.
Agents do not send raw interactive terminal input through these APIs.

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
actions per session, 64 KiB requests, 128 KiB events and 16 MiB evidence per action,
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
organization selection, asset authorization, approvals, handoff, audit access and
reverse-proxy behavior against isolated assets.
