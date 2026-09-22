# JumpServer PAM Python SDK and Agent

Applications can connect to JumpServer directly with the Python SDK or run a Linux Agent on the application host. Clients fetch rotation credentials at startup and keep a signed Credential Event Stream WebSocket open for subscription-account snapshots and later updates. Only `credential.updated` or a newer reconnect snapshot triggers a fetch.

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

Selecting a credential in an access configuration does not add account authorization. The Agent cannot fetch a credential while authorization is incomplete.

### Create an Agent access configuration

1. Open **Access configurations** in the target credential policy and select **Create**.
2. Select a bound application and **Agent access**. The current policy is selected automatically; you can also add other policies bound to that application.
3. Enter the application runtime user and installation path. The default path is `/opt/jumpserver-pam`.
4. Select one delivery mode and save.

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

Find `<configuration-id>` in the access configuration detail. The installation path, application user, socket path, and allowed systemd operation are pinned during installation. Expanding these permissions requires reinstalling the Agent.

### Install the Agent

1. Open the Agent access configuration and select **Generate installation command**.
2. Copy the complete command to the application host and run it within ten minutes. The registration material can be used only once.
3. The command creates a Python virtual environment, installs `jms-pam` from PyPI, registers the Agent, and starts a dedicated systemd service.

Do not assemble or retain the command manually because it contains single-use registration material.

Check the installed service:

```bash
sudo systemctl status jms-pam-agent-<configuration-id>.service --no-pager
```

Use the configured application runtime user to check the local endpoint:

```bash
sudo -u <app-user> curl --fail --silent --show-error \
  --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/health
```

Example healthy response:

```json
{"status":"ok","sync_status":"success"}
```

Return to **Access configurations** in the credential policy detail. The instance should show **Agent online** and **Synced**. The Agent synchronizes at startup, reacts immediately to credential events, and performs a low-frequency reconciliation as a disconnect fallback.

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
sudo -u <app-user> /opt/jumpserver-pam/venv/bin/jms-pam-agent confirm \
  <credential-key> \
  --revision <revision> \
  --socket /run/jumpserver-pam/<configuration-id>/agent.sock
```

Production applications should call the local confirmation endpoint automatically after validating a real connection and completing the switch. The command above is primarily for diagnostics and manual recovery. The Agent persists the confirmation locally first, reports it through the confirmation API, and retries during later reconciliation if Core is temporarily unavailable.

A successful response contains `key`, `revision`, `account_id`, and `status: confirmed` (or `pending` while Core is unavailable). Confirmation is idempotent. Never confirm merely because a file was written, a service restarted, or an event arrived.

## Complete example: rotate one credential

Continue with the alternating rotation policy already connected above.

1. Open the policy under **PAM Integration > Credential Policies** and select **Start rotation**.
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
curl --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/health
```

- `status: ok`: the Agent permits local credential access.
- `status: denied`: the Agent identity is disabled or its protocol version is unsupported; local credential access is denied.
- `sync_status: success`: the most recent configuration and credential synchronization succeeded.

### Fetch a credential

With Unix Socket delivery, fetch the current cache by credential key:

```bash
curl --fail --silent --show-error \
  --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/credentials/<credential-key>
```

The response contains the password. Never write the response, request debug output, or credential files to logs.

### Confirm a credential

Only alternating dual-account rotation requires confirmation. Production applications should call the local endpoint after the new credential passes a real connection check and the switch completes. The installed command is for diagnostics and manual recovery; the application does not need to store Agent keys:

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm \
  <credential-key> \
  --revision <revision> \
  --socket /run/jumpserver-pam/<configuration-id>/agent.sock
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
sudo systemctl status jms-pam-agent-<configuration-id>.service --no-pager

# Show recent logs
sudo journalctl -u jms-pam-agent-<configuration-id>.service -n 100 --no-pager

# Follow logs
sudo journalctl -u jms-pam-agent-<configuration-id>.service -f

# Restart; startup performs an immediate synchronization
sudo systemctl restart jms-pam-agent-<configuration-id>.service

# Upgrade the Agent, then restart it
sudo /opt/jumpserver-pam/venv/bin/pip install --upgrade jms-pam
sudo systemctl restart jms-pam-agent-<configuration-id>.service
```

During a temporary network outage, the Agent retains its last valid cache and retries. If the access configuration is disabled, authorization is revoked, or Core requires an upgrade, the Agent stops returning passwords through the socket but does not delete previously written files.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Complete Python SDK integration

An SDK access configuration accepts one policy mode. Create separate configurations for subscriptions and rotation; each generates its own focused example.

### Prerequisites

1. Create a **Credential update subscription** or **Alternating dual-account rotation** policy under **PAM Integration > Credential Policies** and bind the application. A subscription automatically covers every account authorized to that application; only alternating rotation selects two asset accounts on the policy.
2. Create or open the target application and authorize its asset accounts from the **Accounts** page. For alternating rotation, authorize both policy accounts.
3. Open **Access configurations** in the target credential policy, create an SDK configuration, and select policies of the same mode. The current policy is selected automatically.
4. Open the SDK configuration, select **Generate**, download `jms_pam_config.py`, and protect it as secret material.

Every application process or connection pool must use a stable, unique `instance_id`. Reuse the identifier when redeploying the same instance; never share one identifier across instances.

### Install and configure

The SDK requires Python 3.9 or later. Install it from PyPI with the Python interpreter or virtual environment used by the application:

```bash
python3 -m pip install --upgrade jms-pam
```

Place `jms_pam_config.py` where the application can import it. It contains application identity material; never commit it to source control or write it to logs.

### Credential update subscription

Look up an account ID under Application Management, then fetch any authorized account directly:

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    response = client.GetCredential(models.GetCredentialRequest(
        AccountId='<account-id>',
    ))
    password = response.Account.Secret
```

Long-running applications listen to the Credential Event Stream. Initial and reconnect snapshots also provide the current accounts:

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


def fetch_credential(client, account_id):
    response = client.GetCredential(models.GetCredentialRequest(AccountId=account_id))
    address = response.Asset.Address
    username = response.Account.Username
    secret_type = response.Account.SecretType
    secret = response.Account.Secret
    # Update the application connection with the new credential. Never log secret.


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    for event in client.WatchCredentialEvents():
        if event.get('event') == 'snapshot':
            updates = event.get('credentials', [])
        elif event.get('event') == 'credential.updated':
            updates = [event]
        else:
            continue
        for update in updates:
            account_id = update.get('account_id')
            if update.get('credential_mode') == 'subscription' and account_id:
                fetch_credential(client, account_id)
```

Subscriptions need neither `credential_keys` nor `ConfirmCredential`. Lifecycle events are informational and do not trigger a fetch.

### Alternating dual-account rotation

A rotation configuration contains one stable key per policy. Fetch at startup and after update events or reconnect snapshots. Confirm only after the application validates and activates the new connection:

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import confirmation_keys, cred, credential_keys, profile


def switch_credential(client, key):
    response = client.GetCredential(models.GetCredentialRequest(Key=key))
    # Build and validate a connection, then switch the application connection pool.
    if key in confirmation_keys:
        client.ConfirmCredential(models.ConfirmCredentialRequest(
            Key=response.Key,
            Revision=response.Revision,
            AccountId=response.Account.Id,
        ))


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    for key in credential_keys:
        switch_credential(client, key)
    for event in client.WatchCredentialEvents():
        if event.get('event') == 'snapshot':
            updates = event.get('credentials', [])
        elif event.get('event') == 'credential.updated':
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get('credential_key') or update.get('key')
            if key in credential_keys:
                switch_credential(client, key)
```

`Account.Secret` contains the password or key material identified by `Account.SecretType`. Never log secrets or authentication headers.

### Complete one credential rotation

1. Open the policy under **PAM Integration > Credential Policies** and select **Start rotation**.
2. JumpServer switches the active account and sends `credential.updated`.
3. Call `GetCredential` for the event key, build and validate a connection with the new account, switch successfully, then call `ConfirmCredential`. Lifecycle events are informational and do not trigger a fetch.
4. After every participating instance confirms, select **Continue rotation**, then create and run the password-change task for the previous account.
5. Check the password-change result. On success, the rotation completes with the current account unchanged; the next rotation switches in the opposite direction.

### Common SDK methods

The synchronous client provides these common methods:

- `GetCredential`: use `Key` for alternating rotation or `AccountId` for update subscriptions; provide exactly one.
- `ConfirmCredential`: for alternating rotation only, confirm that the application has validated and is using a revision.
- `WatchCredentialEvents`: block while listening for credential events and reconnect snapshots.

WebSocket Ping/Pong maintains connection liveness; there is no HTTP heartbeat endpoint. Keep low-frequency revision reconciliation only as a recovery path.

HTTP, authentication, network, and response parsing failures are raised as `jms_pam.common.exception.JumpServerPAMSDKException`. Use its `code`, `status_code`, `detail`, and `original_error` fields at the application's retry boundary. Never log credentials or authentication headers.

<!-- sdk-doc:end -->
