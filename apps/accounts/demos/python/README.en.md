# JumpServer PAM Python SDK and Agent

Applications can connect to JumpServer directly with the Python SDK or run a Linux Agent on the application host. The Agent synchronizes credentials through outbound requests and exposes health, credential, and confirmation operations over a local Unix socket.

## Choose an integration

| Method | Use when | Application responsibility |
| --- | --- | --- |
| Python SDK | The application can change Python code and reach JumpServer directly | Poll credentials, switch connections, confirm revisions, and send heartbeats |
| Linux Agent | The application should not store JumpServer keys, or needs file, EnvironmentFile, or Unix Socket delivery | Load and validate Agent-delivered credentials, then confirm the revision actually in use |

<!-- agent-doc:start -->

## Complete Linux Agent setup

This walkthrough uses single-account rotation with JSON file delivery. It starts with data preparation and finishes with Agent installation, the first credential fetch, and one complete credential rotation.

### Prerequisites

Confirm the following before starting:

- The Agent host uses systemd, has Python 3.9 or later, and can reach the JumpServer Core address.
- You have `sudo` access on the Agent host and the application runtime user already exists.
- JumpServer can connect to the target asset and account.
- The application and Agent run on the same host. A containerized application must share the Agent Unix socket directory and use a matching application-user UID.

### Create an application credential

1. Open **Application Management > Application Credentials** and create an application credential.
2. Select **Account rotation** as the credential type and **Single-account rotation** as the rotation mode.
3. Select the asset and account to deliver to the application, then save.
4. Record the **Credential key** from the detail page. Commands use this value, not the credential name.

### Authorize application accounts

1. Open or create the target application under **Application Management**.
2. Authorize the asset account used by the application credential from the application's **Accounts** page.
3. For dual-account rotation, authorize both the primary and backup accounts.

Selecting a credential in Client Access does not add account authorization. The Agent cannot fetch a credential while authorization is incomplete.

### Create an Agent access configuration

1. Open **Client Access** in the application detail and select **Create**.
2. Select **Agent access** and the application credential created above.
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

Return to the Client Access detail in JumpServer. The instance should show **Agent online** and **Synced**. The Agent synchronizes every 30 seconds by default and synchronizes immediately at startup.

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

Production applications should call the local confirmation endpoint automatically after validating a real connection and completing the switch. The command above is primarily for diagnostics and manual recovery. The Agent persists the confirmation locally first, then retries reporting it to Core through heartbeats, so a temporary Core outage does not require the application to confirm again.

A successful response contains `key`, `revision`, `account_id`, and `status: accepted`. Confirmation is idempotent. Never confirm merely because a file was written, a service restarted, or a Webhook arrived.

## Complete example: rotate one credential

Continue with the single-account rotation credential already connected above.

1. Open the credential under **Application Management > Application Credentials** and select **Start rotation**.
2. Create the account password-change task when prompted. After saving, run it from the task list.
3. Wait for the task to finish, return to the credential detail, and select **Check password-change result**.
4. After a successful password change, JumpServer publishes a new credential revision. The Agent fetches and delivers it during its next synchronization.
5. The application loads the new credential, validates a real connection, switches successfully, and confirms the actual `revision` returned by the file or local endpoint.
6. Verify that every Agent instance is reported in the **Waiting for applications** section.
7. Select **Continue rotation**. The flow is complete when the status becomes **Rotation completed**.

Do not copy a revision from this document. Confirm the revision actually loaded by the application; the Agent rejects stale revisions.

If password change fails before the password is modified, fix the network, port, or execution environment and select **Retry**. If the status is **Password verification required**, test the candidate credential from **Password change result** before continuing.

### Dual-account rotation differences

Dual-account rotation requires two application switches:

1. JumpServer publishes the backup account and waits for every instance to load, validate, and confirm it.
2. The primary account password can be changed only after every instance confirms the backup account.
3. JumpServer publishes the primary account again after password change and waits for every instance to confirm it.
4. Rotation completes after every instance switches back to the primary account.

An enabled instance that is offline or has not confirmed the current revision blocks the next step. Give every application instance a stable, unique instance identifier.

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

Production applications should call the local endpoint after the new credential passes a real connection check and the switch completes. The installed command is for diagnostics and manual recovery; the application does not need to store Agent keys:

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

A successful local response means the confirmation is durably stored. The Agent keeps reporting it in later heartbeats until Core accepts it, so a temporary Core outage does not block local confirmation.

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

This walkthrough uses a single-account rotation credential and covers SDK configuration, the first fetch, application confirmation, and one complete rotation.

### Prerequisites

1. Create a **Single-account rotation** credential under **Application Management > Application Credentials** and record its credential key.
2. Create or open the target application and authorize the credential's asset account from the **Accounts** page.
3. Create an SDK configuration under the application's **Client Access** page and select the credential.
4. Open the SDK configuration, select **Generate**, download `jms_pam_config.py`, and protect it as secret material.

Every application process or connection pool must use a stable, unique `instance_id`. Reuse the identifier when redeploying the same instance; never share one identifier across instances.

### Install and configure

The SDK requires Python 3.9 or later. Install it from PyPI with the Python interpreter or virtual environment used by the application:

```bash
python3 -m pip install --upgrade jms-pam
```

Place `jms_pam_config.py` where the application can import it. It contains application identity material; never commit it to source control or write it to logs.

### Complete example

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile, credential_keys


with credential_client.CredentialClient(
    cred,
    instance_id='order-service-node-1',
    profile=profile,
) as client:
    response = client.GetCredential(
        models.GetCredentialRequest(Key=credential_keys[0])
    )

    new_pool = create_pool(
        username=response.Account.Username,
        password=response.Account.Secret,
    )
    new_pool.check_connection()
    old_pool.close()

    client.ConfirmCredential(models.ConfirmCredentialRequest(
        Key=response.Key,
        Revision=response.Revision,
        AccountId=response.Account.Id,
    ))

    state = models.CredentialState(
        Key=response.Key,
        Revision=response.Revision,
        AccountId=response.Account.Id,
    )
    client.Heartbeat(models.HeartbeatRequest(Credentials=[state]))
```

Schedule credential fetches and heartbeats with the application's own scheduler. Call `ConfirmCredential` only after a new connection has been validated and activated; a successful fetch does not mean the application is using that revision.

### Complete one credential rotation

1. Open the credential under **Application Management > Application Credentials** and select **Start rotation**.
2. Create and run the password-change task, then select **Check password-change result** after it finishes.
3. After JumpServer publishes a new revision, the application's next scheduled `GetCredential` fetches it. A Webhook can also trigger an immediate fetch.
4. Create and validate a connection with the new password, switch successfully, then call `ConfirmCredential`.
5. Verify that every SDK instance has reported from the credential detail, then select **Continue rotation** to finish.

### Common SDK methods

The synchronous client provides these common methods:

- `GetCredential`: fetch the currently published credential and revision.
- `ConfirmCredential`: confirm that the application has validated and is using a revision.
- `Heartbeat`: report instance liveness and the credential revisions already confirmed in use.

The SDK starts no background threads. The application must poll credentials and send heartbeats. A Webhook can trigger an immediate `GetCredential`, but periodic polling should remain as a recovery path.

HTTP, authentication, network, and response parsing failures are raised as `jms_pam.common.exception.JumpServerPAMSDKException`. Use its `code`, `status_code`, `detail`, and `original_error` fields at the application's retry boundary. Never log credentials or authentication headers.

<!-- sdk-doc:end -->
