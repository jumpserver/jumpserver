# JumpServer PAM Python SDK and Go Agent

Applications can connect to JumpServer directly with the Python SDK or run the Go Agent on the application host. The Agent runs in the foreground on Linux, macOS and Windows; its built-in systemd installer is Linux-only. Clients fetch rotation credentials at startup and keep a signed Credential Event Stream WebSocket open for subscription-account snapshots and later updates. Credential updates, newer reconnect snapshots and manual account switch requests trigger a fetch.

## Source and local installation

The Python SDK is distributed as `jms-pam`. The standalone Go Agent is maintained under `apps/accounts/clients/go`:

- `jms_pam/client.py`: public SDK operations for credentials, synchronization and commands.
- `jms_pam/_transport.py`, `_events.py`, and `_commands.py`: HTTP session ownership, event streams and command execution.
- `jms_pam/models.py`: typed dataclass responses with `snake_case` fields.
- `jms_pam/exceptions.py`: the common `PAMError` exception.
- `../go/cmd/jms-pam-agent`: the standalone Go Agent entry point; runtime code lives in `../go/agent`.
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

## Architecture

The Python SDK owns its HTTP session, signatures, event reader and hooks. The standalone Go Agent is built from `go/cmd/jms-pam-agent`; its configuration, delivery, runtime and local API live in `go/agent`. Local rules select templates, file targets and bounded service or script actions. Latest credentials, delivered revisions and explicit application confirmations are persisted separately.

## Manually start a policy cycle

Use **Start new cycle** in the policy's Basic settings or Event reception. The new cycle's timeline opens automatically:

- Credential subscriptions publish `credential.updated` again for currently authorized accounts, sharing a new `operation_id`. Passwords and revisions stay unchanged, and no secret-change start, success or failure events are generated. SDK clients fetch using the event key. The Agent also refetches unchanged revisions without repeating delivery or restarting services. Receipts indicate notification reception. Offline clients obtain the current snapshot when reconnecting.
- Account rotation starts a new cycle after the previous cycle has completed or been cancelled. JumpServer verifies the backup account, then publishes the switch. Clients apply and confirm the backup. Applications that recently used the original account through the legacy secret API must also fetch the backup after publication. The original account must have no successful JumpServer secret fetches for the configured period (7 days by default) after publication before its secret can be changed. Another source-account fetch restarts the window. Verification, switching, observation, and secret change share one cycle.

Administrator API: `POST /api/v1/accounts/application-credentials/<policy-id>/start-cycle/` requires policy change permission and, for account rotation, account verification permission. It returns `credential` and `cycle_id`. Disabled policies and unfinished rotations cannot start another cycle. Subscription accounts must finish any running secret changes before republishing.

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
| Go Agent | The application should not store JumpServer keys, or needs file, EnvironmentFile, or local Socket delivery | Load and validate Agent-delivered credentials, then confirm the revision actually in use |

<!-- agent-doc:start -->

## Go Agent integration

The built-in service installer requires Linux and root. Download `jms_pam_agent.json` from the Agent access wizard and install the Go binary with a stable instance ID. Linux service configuration is `/etc/jms-pam-agent/agent.json`; the fixed service is `jms-pam-agent`.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

For macOS, non-root Linux or Windows foreground use, select JSON or Socket delivery in the wizard and follow its `init-local` and `run --local --config` commands. Initialize only once, then reuse the generated local configuration on restart. Foreground mode uses the current user and does not perform systemd actions; Windows files use private ACLs instead of POSIX mode bits.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

Choose JSON for files, EnvironmentFile for a pinned systemd service, or Unix Socket for local API access. The Agent records delivered revisions after delivery succeeds; the application validates and applies credentials before recording an applied revision. The socket belongs to the configured application user with mode 0600; make local requests as that user.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

The systemd unit must reference the EnvironmentFile. Use reload only if the application rereads it; reload does not inject new environment variables into a running process. Installation pins the allowed paths, user, service and action; expanding them requires reinstallation.

Local rules configure target files, JSON/EnvironmentFile rendering or trusted templates, and an optional systemd reload/restart or fixed executable. Scripts receive credential JSON on stdin, use fixed arguments, have a bounded timeout and must validate their application before returning success. Core cannot add script paths or expand local capabilities. Restart the Agent after editing its private configuration.

The downloaded bootstrap contains Agent identity and delivery settings. Edit rules to declare the account IDs used by the business, update its configuration, activate the change and verify the running connection. An account selector with allow_account_switch also follows A/B rotation in either direction. Optional credential_check validates the new login before file changes. The Agent supplies default state, event and socket paths and a 300-second reconciliation interval. Empty rules write one default file per delivered credential.

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "app_user": "orders"
  },
  "rules": []
}
```

`rules`:

```json
[
  {
    "accounts": [
      {
        "account_id": "<primary-account-id>",
        "allow_account_switch": true,
        "fields": {
          "DB_USER": "username",
          "DB_PASSWORD": "secret"
        }
      }
    ],
    "config_update": {
      "file": "/etc/order-service/config.yml"
    },
    "service_action": {
      "unit": "order-service.service",
      "operation": "restart"
    },
    "application_check": {
      "path": "/usr/local/libexec/jms-pam/check-running-db",
      "confirm_on_success": true
    }
  }
]
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```

### Local API and confirmation

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

For alternating rotation, validate a real connection, switch the application connection pool and release old connections before confirming the exact key, revision and account_id. Credential change subscriptions require no confirmation. A failed connection check must prevent confirmation.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

Only alternating rotation uses confirm. A local confirmation is persisted first; status confirmed means Core accepted it, while pending means it will be retried. Do not confirm merely because a file was written or a service restarted.

### Troubleshooting

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

The Agent reconciles on startup, on relevant events and every 300 seconds. Network failures retain the latest authorized credentials. Identity or authorization rejection blocks socket retrieval; successful signed synchronization restores it. Previously written files remain. SIGINT/SIGTERM closes the server, connections and reader thread.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Complete Python SDK integration

The SDK uses the application’s AK/SK and receives every active policy bound to that application. One connection can handle both subscriptions and rotation. The application access wizard provides an example that dispatches by policy mode; binding changes take effect automatically.

### Prerequisites

1. Create a **Credential change subscription** or **Account rotation** policy under **PAM Integration > Credential Policies** and bind the application. Select the accounts that should trigger subscription notifications; account rotation currently selects two accounts on the same asset.
2. Create or open the target application and authorize its asset accounts from the **Accounts** page. For alternating rotation, authorize both policy accounts.
3. Open the application’s **Access and connections** page, select **Access wizard**, and choose **SDK access**.
4. Generate and download `jms_pam_config.py` and use the example code. No configuration ID or policy list is required.

The wizard writes a generated `instance_id` into `jms_pam_config.py`. Reuse that file when recreating a container to preserve its identity. Generate separate materials for each replica, or set a distinct, stable `JMS_INSTANCE_ID` for each one.

### Install and configure

The SDK requires Python 3.9 or later. Download and extract the SDK archive from JumpServer, then install from its root using the application’s Python interpreter or virtual environment:

```bash
python3 -m pip install .
```

Place `jms_pam_config.py` where the application can import it. It contains application identity material and the generated instance ID; never commit it to source control or write it to logs.

### Subclass event handlers

Applications with account mappings or connection pools can subclass `Client` and override its hooks. Keep `__init__` for local state; `watch_events()` receives the initial snapshot, fetches credentials by policy mode and calls `on_credential_changed`. Updates and reconnect snapshots use the same hook.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


class MyClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}

    def on_credential_changed(self, credential):
        # Validate the new connection and switch the application's connection pool.
        raise NotImplementedError("Implement the application connection update first")
        # Save after a successful switch: self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        # Release affected connections; the next snapshot reconciles the full scope.
        self.credentials.pop(event.get("credential_key"), None)


with MyClient(instance_id=instance_id, **client_options) as client:
    client.watch_events()  # Blocks until stopped; dispatches to the subclass hooks.
```

Use `start_events()` instead to start a background listener and return immediately. `stop_events()` stops the listener and waits for an active hook, while leaving the HTTP client usable. Exiting `with` or calling `close()` stops event streams and waits for hooks before closing HTTP resources. Each client allows one hook listener; it can restart after `stop_events()`. Hooks may also stop or close their own client.

The reader and serial hook worker use a bounded queue of 128 events. Slow hooks do not immediately pause reading; a full queue applies backpressure. Failed credential fetches or `on_credential_changed` calls retry with 1–30 second exponential backoff, fetching the current credential again. Newer updates replace pending retries for the same account or key. Snapshots replace the retry scope; revocation/configuration changes clear pending retries until the following snapshot. Handlers must be idempotent, and reconnect snapshots may call them again even at the same revision.

`on_event(event)` observes each raw event before credential hooks. Override it for snapshot state reconciliation, configuration/lifecycle events or commands; command handlers must still use `execute_application_command`. `on_credential_revoked(event)` handles revocation. `on_event_error(error, event)` receives failures, with `event=None` for a fatal reader error; its default logs only the exception type. Observer and revocation hooks are not automatically retried. See `subclass_demo.py` for snapshot state reconciliation.

`start_events()` returning does not mean initial credentials are ready. If startup depends on them, use a `threading.Event` in the subclass and wait before serving requests. Background hooks run concurrently with the main application; protect shared application state as needed. The SDK never automatically confirms rotation: call `confirm_credential` inside your successful business handler only for rotation policies. `clone()` constructs fresh subclass state with an independent HTTP session; override it if your subclass requires additional constructor arguments.

The existing `watch_credential_events(stop_event=...)` iterator remains available with its original receipts, blocking and cancellation semantics. The examples below retain that calling style.

### Credential change subscription

Look up an account ID under Application Management, then fetch any authorized account directly:

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    response = client.get_credential(
        account_id="<account-id>",
    )
    password = response.account.secret
```

Long-running applications listen to the Credential Event Stream. Initial and reconnect snapshots also provide the current accounts:

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def fetch_credential(client, key):
    response = client.get_credential(key=key, allow_local_fallback=False)
    address = response.asset.address
    username = response.account.username
    secret_type = response.account.secret_type
    secret = response.account.secret
    # Update the application connection with the new credential. Never log secret.


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            account_id = update.get("account_id")
            key = update.get("credential_key") or update.get("key")
            if update.get("credential_mode") == "subscription" and account_id and key:
                if not key.endswith(f":{account_id}"):
                    key = f"{key}:{account_id}"
                fetch_credential(client, key)
```

Subscriptions need neither `credential_keys` nor `confirm_credential`. Lifecycle events are informational and do not trigger a fetch.

### Alternating dual-account rotation

The event snapshot supplies one stable key per rotation policy. Fetch after the initial snapshot and after update events or reconnect snapshots. Confirm only after the application validates and activates the new connection:

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError("Implement connection validation, pool switching and old connection cleanup")


def switch_credential(client, key):
    response = client.get_credential(key=key, allow_local_fallback=False)
    apply_credential(response)
    client.confirm_credential(
        key=response.key,
        revision=response.revision,
        account_id=response.account.id,
    )


with Client(instance_id=instance_id, **client_options) as client:
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

- `get_credential`: use `account_id` for application-authorized pull, `key=account:<account-id>` for push subscriptions, or a policy key for alternating rotation; provide exactly one selector.
- `confirm_credential`: for alternating rotation only, confirm that the application has validated and is using a revision.
- `watch_events` / `start_events` / `stop_events`: run subclass hooks in the foreground or background and stop them.
- `watch_credential_events`: block while listening for credential events and reconnect snapshots.
- `list_application_commands` / `execute_application_command`: poll, claim and report application commands.
- `sync_agent`: reconcile retained and delivered `KnownRevision` values with Core.
- `clone`: create an independent HTTP session; `close` or a `with` statement releases sessions and event streams.

Before yielding a business event, the SDK automatically sends a best-effort receipt. The receipt only means the SDK/Agent has read the event; it does not mean credentials were fetched or applied, and it does not replace `confirm_credential`. Receipt failures do not prevent event processing. Update and restart existing SDK/Agent deployments to report receipts. Reconnect snapshots restore current credential versions; they do not replay past events or create receipts for them.

WebSocket Ping/Pong maintains connection liveness; there is no HTTP heartbeat endpoint. Keep low-frequency revision reconciliation only as a recovery path.

HTTP, authentication, network, and response parsing failures are raised as `jms_pam.PAMError`. Use its `code`, `status_code`, `detail`, and `original_error` fields at the application's retry boundary. Never log credentials or authentication headers.

### Latest credentials and backend outages

Credential getters always request the API first. A successful fetch replaces the retained latest credential; older revisions never overwrite a newer one. The retained value has no time expiry. Only a timeout, network failure or HTTP 5xx may return this value for the same selector, marked as coming from local state. Without a previously fetched value, the original error is raised. SDK values stay in the current client’s memory until replacement, revocation or close; clones and process restarts start empty. The Agent retains its latest credentials in its existing protected local state. HTTP 401/403/404 or client_upgrade_required clear SDK retained values and raise; malformed successful responses also raise. Explicit revocations remove affected credentials, and snapshots remove push entries outside the subscribed scope. A configuration notification retains existing values until the following snapshot reconciles scope. The Agent applies explicit revocation and reduced snapshot scope before HTTP synchronization, persists the reduced scope, and blocks affected local reads even during a backend outage or after restart. A credential_not_found response (HTTP 400) also clears retained SDK values. Direct account_id pull always requires a live API response; push snapshots do not authorize cached pull values.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

With managed event listening enabled, snapshot and credential.updated automatically fetch the current credential, replace the retained value and then invoke the business hook. A failed refresh leaves the previous value in place and retries. The Agent also refetches on update notifications and retains its previous credentials during backend outages. Refresh and manual switching use the live-only calls below; a retained password must not be treated as a newly fetched revision or automatically confirmed.

Event connections send application ping messages at 10-second intervals while idle and reconnect after approximately 30 seconds without messages. Reconnect uses 1–30 second exponential backoff and fresh signatures. Reconnect snapshots restore current state; past events are not replayed.

<!-- sdk-doc:end -->
