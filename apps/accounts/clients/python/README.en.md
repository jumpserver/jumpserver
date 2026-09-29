# JumpServer PAM Python SDK and Agent

Applications can connect to JumpServer directly with the Python SDK or run a Linux Agent on the application host. Clients fetch rotation credentials at startup and keep a signed Credential Event Stream WebSocket open for subscription-account snapshots and later updates. Credential updates, newer reconnect snapshots and manual account switch requests trigger a fetch.

## Source and local installation

The Python SDK and Linux Agent are maintained together in `apps/accounts/clients/python` and distributed as `jms-pam`:

- `jms_pam/client.py`: public SDK operations for credentials, synchronization and commands.
- `jms_pam/_transport.py`, `_events.py`, and `_commands.py`: HTTP session ownership, event streams and command execution.
- `jms_pam/models.py`: typed dataclass responses with `snake_case` fields.
- `jms_pam/exceptions.py`: the common `PAMError` exception.
- `jms_pam/agent.py`: the `jms-pam-agent` entry point; runtime code lives in `jms_pam/_agent/`.
- `demo.py`, `postgresql_app.py`, and `file_apps/`: example applications that use the SDK or Agent.

Install from the repository root:

```bash
python3 -m pip install -e ./apps/accounts/clients/python
```

You can also download the Python SDK archive from JumpServer and run `python3 -m pip install .` from its extracted root, then run the examples from the same directory.

## Python interface conventions

Methods, parameters, and response attributes use `snake_case`; classes use `CapWords`. Configure the client with keyword arguments, pass operation arguments directly, and use typed responses. A context manager closes the HTTP session:

```python
from jms_pam import Client

with Client(
    "https://jumpserver.example.com",
    app_id="<app-id>",
    app_secret="<app-secret>",
    instance_id="orders-worker-1",
) as client:
    credential = client.get_credential(key="<credential-key>")
    username = credential.account.username
    password = credential.account.secret
```

The original request-object API under `jms_pam.credential.v1` remains available for compatibility and emits `DeprecationWarning`. New integrations use the `Client` API shown here. Regenerate SDK access configuration when migrating to it.

## Internal architecture and execution

The SDK decodes and validates responses at the network boundary. Business code uses dataclasses directly; file and local API delivery project them to the delivery format. Compatibility APIs reuse the same HTTP, event stream and command lifecycle.

The Agent separates responsibilities under `jms_pam/_agent/`:

| Module | Responsibility |
| --- | --- |
| `runtime.py` | Reconcile authorization and revisions, process events and commands, retain application confirmations |
| `config.py` | Validate remote configuration against installed capabilities without creating directories |
| `storage.py` | Private state, atomic writes and protected paths |
| `delivery.py` | JSON, EnvironmentFile and Socket delivery data |
| `server.py` | Local HTTP API over a Unix socket |
| `install.py` | Bootstrap registration and systemd installation |

The event reader sends receipts and queues messages. One runtime thread performs synchronization, delivery and commands in order. The bounded queue waits when reconciliation is busy. By default, reconciliation and command polling also run every 300 seconds. A failed event or command does not stop later work.

Reconciliation reads the authorized scope and revisions, validates configuration, fetches and caches credentials, delivers a stable snapshot, then records delivered revisions. Explicit application confirmation stores the applied revision and reports it to Core; subsequent synchronization retries pending confirmations. Cached, delivered and applied revisions remain separate. Failed writes or service actions do not mark delivery complete.

Each `Client` owns one HTTP session and serializes its requests. Use `clone()` for an independent session. `close()` also closes active event streams; a closed client cannot be reused. Event listeners accept a `threading.Event` for cancellation. Both normal and abnormal disconnects close the old connection before reconnecting with a 1–30 second backoff. SIGINT and SIGTERM stop the Agent's connections, local server and reader thread.

Temporary network failures retain previously authorized cache access. Disabled identities or rejected authorization snapshots disable local credential access until a successful signed sync. Logs record error codes or exception types, avoiding credential data in server exception messages.

## Manually start a policy cycle

Use **Start new cycle** in the policy's Basic settings or Event reception. The new cycle's timeline opens automatically:

- Credential subscriptions publish `credential.updated` again for currently authorized accounts, sharing a new `operation_id`. Passwords and revisions stay unchanged, and no secret-change start, success or failure events are generated. SDK clients fetch using the event key. The Agent also refetches unchanged revisions without repeating delivery or restarting services. Receipts indicate notification reception. Offline clients obtain the current snapshot when reconnecting.
- Account rotation starts a new preparation cycle after the previous cycle has completed or been cancelled. Align the current account, observe the configured standby no-traffic period (7 days by default), then let the administrator initiate switching. Preparation, switching and secret changes share the same cycle.

Administrator API: `POST /api/v1/accounts/application-credentials/<policy-id>/start-cycle/` requires policy change permission and returns `credential` and `cycle_id`. Disabled policies and unfinished rotations cannot start another cycle. Subscription accounts must finish any running secret changes before republishing.

## Manually send application events

Use **More > Send event** in the application list or **Event processing > Send event** in application details. Select the event, connection instances and deadline.

- `credential.switch.requested` asks an application to apply the currently published account and version. It does not change the policy's active account; use the rotation workflow for that. Fetch the credential, verify the requested account and revision, apply it, call `confirm_credential`, then report success.
- `application.restart.requested` invokes an SDK application's own restart handler and health check. The Agent only restarts the systemd service configured for EnvironmentFile delivery with the restart action, then checks that it is active.

The WebSocket receipt means received, not executed. `execute_application_command(event, handler)` claims the request before calling the handler. Only an `accepted: true` claim runs it; duplicate delivery never repeats the handler. A normal return reports success; an exception reports failure. Implement application-level idempotency and health checks in the handler. Agent switch requests succeed only after the application confirms the actual account version.

Offline instances receive requests on reconnect before their deadline. API applications can instead poll with AK/SK signatures and a stable `instance_id`; the first poll registers an instance that administrators can subsequently target:

1. `GET /api/v1/accounts/credential-client/commands/?instance_id=<instance-id>` returns outstanding requests (`list_application_commands()` in the SDK). Use the credential client's signed headers and protocol version 1.
2. `POST /api/v1/accounts/credential-client/command-result/` with `instance_id`, `command_id` and `status: running`. Execute only when the response says `accepted: true`.
3. Report `status: success` or `status: failed` to the same endpoint, optionally including a non-sensitive `error_code` (`report_application_command_result()` in the SDK).

Expired requests cannot be claimed. If a restart terminates the reporting process, check the application's state before an administrator sends another request. The existing Secret API remains unchanged and does not itself receive manual events.

## Choose an integration

| Method | Use when | Application responsibility |
| --- | --- | --- |
| Python SDK | The application can change Python code and reach JumpServer directly | Listen for events, fetch changed credentials, switch connections, and confirm revisions |
| Linux Agent | The application should not store JumpServer keys, or needs file, EnvironmentFile, or Unix Socket delivery | Load and validate Agent-delivered credentials, then confirm the revision actually in use |

<!-- agent-doc:start -->

## Complete Linux Agent setup

This walkthrough uses alternating dual-account rotation with JSON file delivery. It starts with data preparation and finishes with Agent installation, the first credential fetch, and one complete credential rotation.

### Prerequisites

Confirm the following before starting:

- The Agent host uses systemd, has Python 3.9 or later, and can reach the JumpServer Core address.
- You have `sudo` access on the Agent host and the application runtime user already exists.
- JumpServer can connect to the target asset and account.
- The application and Agent run on the same host. A containerized application must share the Agent Unix socket directory and use a matching application-user UID.

### Create a credential policy

1. Open **PAM Integration > Credential Policies** and create a credential policy.
2. Select **Alternating dual-account rotation**.
3. Select the initial account, alternate account, and one or more bound applications, then save.
4. Record the **Credential key** from the detail page. Commands use this value, not the credential name.

### Authorize application accounts

1. Open or create the target application under **Application Management**.
2. Authorize the asset accounts used by the credential policy from the application's **Accounts** page.
3. For alternating rotation, authorize both accounts.

Application access does not add account authorization. The Agent cannot fetch a credential while authorization is incomplete.

### Use the application access wizard

1. Open the application's **Access and connections** page and select **Access wizard**.
2. Select **Agent access**. Every active policy bound to the application is included automatically; no policy selection is required.
3. Enter the application runtime user and installation path. The default path is `/opt/jumpserver-pam`.
4. Select one delivery mode, then generate and download the installation materials.

| Delivery mode | Agent behavior | Application behavior |
| --- | --- | --- |
| JSON file | Writes one `<credential-key>.json` file per credential | Watch or periodically read the file, validate a new connection, then confirm the revision |
| systemd EnvironmentFile | Writes `<credential-key>.env`, then runs the configured `reload` or `restart` | Reference the file from the systemd service, then confirm after startup or reload and connection validation succeed |
| Unix Socket | Keeps the credential in memory and serves it over a local socket | Fetch from the local endpoint, validate a new connection, then call the confirmation endpoint |

EnvironmentFile delivery requires the application systemd unit to reference the generated file in advance:

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

Prefer `restart`. Use `reload` only when the application's reload handler explicitly rereads the EnvironmentFile; a systemd reload does not inject new environment variables into an already running process.

Find `<configuration-id>` in the downloaded bootstrap file’s `configuration_id` field. The installation path, application user, socket path, and allowed systemd operation are pinned during installation. Expanding these permissions requires reinstalling the Agent.

### Install the Agent

1. Prepare a Linux host with systemd, Python 3.9+, and the application runtime user.
2. Copy the downloaded `jms_pam_agent.json` to that host and run the wizard's installation command from its directory. The Agent signs API and WebSocket requests with the application's AK/SK.
3. Return to the application's **Access and connections** page and verify the instance is **Online**.

The download contains the application's AK/SK. Restrict its permissions and delete the bootstrap download after installation. The installed Agent keeps its configuration readable by root only.

Check the installed service:

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
```

Use the configured application runtime user to check the local endpoint:

```bash
sudo -u '<app-user>' curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health
```

Example healthy response:

```json
{"status":"ok","sync_status":"success"}
```

Return to the application’s **Access and connections** page to check its instances. The Agent synchronizes at startup, reacts immediately to credential events, and performs a low-frequency reconciliation as a disconnect fallback.

### Load and confirm the first credential

The default JSON file path is:

```text
/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json
```

The file has a fixed schema containing `key`, `revision`, asset and account metadata, `username`, `secret_type`, and `secret`. The application must process it in this order:

1. Read the complete file and compare its `revision` with the current revision.
2. Create a connection with the new credential and run a real, low-impact check such as database `SELECT 1`.
3. Atomically switch the connection pool or application configuration.
4. Confirm the revision only after the switch succeeds.

```bash
sudo -u '<app-user>' /opt/jumpserver-pam/venv/bin/jms-pam-agent confirm \
  '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

Production applications should call the local confirmation endpoint automatically after validating a real connection and completing the switch. The command above is primarily for diagnostics and manual recovery. The Agent persists the confirmation locally first, reports it through the confirmation API, and retries during later reconciliation if Core is temporarily unavailable.

A successful response contains `key`, `revision`, `account_id`, and `status: confirmed` (or `pending` while Core is unavailable). Confirmation is idempotent. Never confirm merely because a file was written, a service restarted, or an event arrived.

## Complete example: rotate one credential

Continue with the alternating rotation policy already connected above.

1. Open the policy under **PAM Integration > Credential Policies** and select **Start new cycle**. After applications align on the current account, observe the configured standby interval without Secret API access (7 days by default). The initiating administrator receives a readiness notification and manually selects **Start rotation**.
2. JumpServer publishes the other account and sends `credential.updated`.
3. Every enabled Agent instance fetches, delivers, and confirms that revision after the application switches successfully.
4. After all participating instances confirm, create and run the password-change task for the account that was replaced.
5. Check the password-change result. The other account remains active when the rotation completes; the next rotation switches in the opposite direction.

Do not copy a revision from this document. Confirm the revision actually loaded by the application; the Agent rejects stale revisions.

If password change fails before the password is modified, fix the network, port, or execution environment and select **Retry**. If the status is **Password verification required**, test the candidate credential from **Password change result** before continuing.

An enabled instance whose WebSocket is offline or that has not confirmed the target revision blocks password change. Give every application instance a stable, unique instance identifier.

## Agent local endpoints

The Agent exposes local operations only on a protected Unix socket and does not listen on a TCP port. The socket is owned by the configured application runtime user and has `0600` permissions by default.

### Health check

```bash
curl --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health
```

- `status: ok`: the Agent permits local credential access.
- `status: denied`: the Agent identity is disabled or its protocol version is unsupported; local credential access is denied.
- `sync_status: success`: the most recent configuration and credential synchronization succeeded.

### Fetch a credential

With Unix Socket delivery, fetch the current cache by credential key:

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

The response contains the password. Never write the response, request debug output, or credential files to logs.

### Confirm a credential

Only alternating dual-account rotation requires confirmation. Production applications should call the local endpoint after the new credential passes a real connection check and the switch completes. The installed command is for diagnostics and manual recovery; the application does not need to store Agent keys:

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm \
  '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

The equivalent local request is:

```http
POST /v1/confirm
Content-Type: application/json

{"key":"<credential-key>","revision":<revision>}
```

A successful local response means the confirmation is durably stored. The Agent reports it through the confirmation API and retries it during later reconciliation, so a temporary Core outage does not block local confirmation.

## Common Agent commands

```bash
# Check status
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager

# Show recent logs
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager

# Follow logs
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -f

# Restart; startup performs an immediate synchronization
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'

# Install the new downloaded SDK directory, then restart the Agent
sudo /opt/jumpserver-pam/venv/bin/pip install --upgrade '<sdk-directory>'
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

During a temporary network outage, the Agent retains its last valid cache and retries. If the application or instance is disabled, authorization is revoked, or Core requires an upgrade, the Agent stops returning passwords through the socket but does not delete previously written files.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Complete Python SDK integration

The SDK uses the application’s AK/SK and receives every active policy bound to that application. One connection can handle both subscriptions and rotation. The application access wizard provides an example that dispatches by policy mode; binding changes take effect automatically.

### Prerequisites

1. Create a **Credential change subscription** or **Account rotation** policy under **PAM Integration > Credential Policies** and bind the application. Select the accounts that should trigger subscription notifications; account rotation currently selects two accounts on the same asset.
2. Create or open the target application and authorize its asset accounts from the **Accounts** page. For alternating rotation, authorize both policy accounts.
3. Open the application’s **Access and connections** page, select **Access wizard**, and choose **SDK access**.
4. Generate and download `jms_pam_config.py` and use the example code. No configuration ID or policy list is required.

Every application process or connection pool must use a stable, unique `instance_id`. Reuse the identifier when redeploying the same instance; never share one identifier across instances.

### Install and configure

The SDK requires Python 3.9 or later. Download and extract the SDK archive from JumpServer, then install from its root using the application’s Python interpreter or virtual environment:

```bash
python3 -m pip install .
```

Place `jms_pam_config.py` where the application can import it. It contains application identity material; never commit it to source control or write it to logs.

### Credential change subscription

Look up an account ID under Application Management, then fetch any authorized account directly:

```python
from jms_pam import Client
from jms_pam_config import client_options


with Client(instance_id="order-service-node-1", **client_options) as client:
    response = client.get_credential(
        account_id="<account-id>",
    )
    password = response.account.secret
```

Long-running applications listen to the Credential Event Stream. Initial and reconnect snapshots also provide the current accounts:

```python
from jms_pam import Client
from jms_pam_config import client_options


def fetch_credential(client, account_id):
    response = client.get_credential(account_id=account_id)
    address = response.asset.address
    username = response.account.username
    secret_type = response.account.secret_type
    secret = response.account.secret
    # Update the application connection with the new credential. Never log secret.


with Client(instance_id="order-service-node-1", **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            account_id = update.get("account_id")
            if update.get("credential_mode") == "subscription" and account_id:
                fetch_credential(client, account_id)
```

Subscriptions need neither `credential_keys` nor `confirm_credential`. Lifecycle events are informational and do not trigger a fetch.

### Alternating dual-account rotation

The event snapshot supplies one stable key per rotation policy. Fetch after the initial snapshot and after update events or reconnect snapshots. Confirm only after the application validates and activates the new connection:

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError("Implement connection validation, pool switching and old connection cleanup")


def switch_credential(client, key):
    response = client.get_credential(key=key)
    apply_credential(response)
    client.confirm_credential(
        key=response.key,
        revision=response.revision,
        account_id=response.account.id,
    )


with Client(instance_id="order-service-node-1", **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get("credential_key") or update.get("key")
            if key and update.get("credential_mode") == "alternating_rotation":
                switch_credential(client, key)
```

`Account.secret` contains the password or key material identified by `Account.secret_type`. Never log secrets or authentication headers.

### Complete one credential rotation

1. Open the policy under **PAM Integration > Credential Policies** and select **Start new cycle**. Applications confirm the current account, then wait for the standby account to receive no Secret API access for the configured interval (7 days by default). After the readiness notification, the administrator manually selects **Start rotation**.
2. JumpServer switches the active account and sends `credential.updated`.
3. Call `get_credential` for the event key, build and validate a connection with the new account, switch successfully, then call `confirm_credential`. Lifecycle events are informational and do not trigger a fetch.
4. After every participating instance confirms, select **Continue rotation**, then create and run the password-change task for the previous account.
5. Check the password-change result. On success, the rotation completes with the current account unchanged; the next rotation switches in the opposite direction.

### Application commands

Use `list_application_commands()` to poll outstanding requests and `execute_application_command(event, handler)` to claim and execute them. The handler runs only when the claim is accepted. For a switch request, verify the requested account and revision, validate and apply the credential, then confirm it. For a restart request, restart the application and verify its health before returning. Handler exceptions report failure; a failed result report preserves the original exception.

### Common SDK methods

The synchronous client provides these common methods:

- `get_credential`: use `key` for alternating rotation or `account_id` for update subscriptions; provide exactly one.
- `confirm_credential`: for alternating rotation only, confirm that the application has validated and is using a revision.
- `watch_credential_events`: block while listening for credential events and reconnect snapshots.
- `list_application_commands` / `execute_application_command`: poll, claim and report application commands.
- `sync_agent`: reconcile cached and delivered `KnownRevision` values with Core.
- `clone`: create an independent HTTP session; `close` or a `with` statement releases sessions and event streams.

Before yielding a business event, the SDK automatically sends a best-effort receipt. The receipt only means the SDK/Agent has read the event; it does not mean credentials were fetched or applied, and it does not replace `confirm_credential`. Receipt failures do not prevent event processing. Update and restart existing SDK/Agent deployments to report receipts. Reconnect snapshots restore current credential versions; they do not replay past events or create receipts for them.

WebSocket Ping/Pong maintains connection liveness; there is no HTTP heartbeat endpoint. Keep low-frequency revision reconciliation only as a recovery path.

HTTP, authentication, network, and response parsing failures are raised as `jms_pam.PAMError`. Use its `code`, `status_code`, `detail`, and `original_error` fields at the application's retry boundary. Never log credentials or authentication headers.

<!-- sdk-doc:end -->
