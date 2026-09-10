# JumpServer PAM Python SDK and Agent

## URL installation

Python 3.9+ and pip are required. Generate configuration in the application's Client Access tab and run its installation command using the application's Python interpreter or virtual environment. Example for a local JumpServer:

```bash
python3 -m pip install --index-url https://pypi.org/simple http://127.0.0.1:8080/api/v1/accounts/python-sdk/
```

The SDK source downloads from JumpServer; build tools such as setuptools and runtime dependencies such as requests download from official PyPI. Both must be reachable during installation. No local packages directory is needed. On another machine, use the generated reachable JumpServer address rather than 127.0.0.1.

For `installing build dependencies` / `No matching distribution found for setuptools` errors, inspect package-index access with `pip -v`. A mirror returning 403 does not mean setuptools is unavailable. The explicit index above applies only to this installation, without changing global pip configuration. If public access is restricted, use an accessible internal index containing these dependencies. Do not hide missing dependencies with `--no-deps` or `--no-build-isolation`.

## Application integration

Fetch a credential by its immutable key, replace and verify the application's connection pool, release the old pool, and then confirm the applied revision:

```python
from jms_pam import JumpServerPAMClient

client = JumpServerPAMClient.from_config('jms-pam.json')

credential = client.get_credential('cred-pg-main')
new_pool = create_pool(username=credential.username, password=credential.secret)
new_pool.check_connection()
old_pool.close()
client.confirm_applied(credential)
```

Create a client access configuration in the application's Client Access tab, select credentials, and download `jms-pam.json`. It includes the endpoint, application credentials, organization and configuration ID. Protect this file as a secret. Before creating the SDK client, explicitly set `instance_id` in the file or `JMS_PAM_INSTANCE_ID` in the environment. Every independent application process/connection pool must have a stable, unique ID across workers and hosts; create clients after forking. Missing IDs, surrounding whitespace, and IDs longer than 128 characters are rejected. There is no hostname fallback or server-side duplicate-session detection; deployment configuration owns uniqueness. Fetch periodically while the application runs; confirm only after successfully applying the returned version. The SDK reports a heartbeat every 30 seconds.

The generated Linux Agent command creates a virtual environment, installs the SDK/Agent from the JumpServer URL using the specified index for dependencies, and registers with JumpServer. Registration material expires in 10 minutes and is single-use. With the Agent installed, run registration using `jms-pam-agent` from its virtual environment:

```bash
sudo jms-pam-agent install \
  --endpoint https://jms.example.com \
  --token one-time-token \
  --instance-id order-service-node-1 \
  --credential cred-pg-main \
  --app-user order-service
```

The Agent atomically writes `/etc/jumpserver-pam/credentials.json`. After the application reloads the file, verifies its new connection, and releases the old connection, confirm it with:

```bash
jms-pam-agent confirm cred-pg-main --revision 2
```

## Managed delivery

When an application cannot read `credentials.json`, a host administrator can add local `deliveries` to `agent.json`. The Agent writes selected fields as a POSIX shell-compatible environment file and runs a local apply program. With `confirmation: apply`, it confirms only after that program exits successfully and the credential is still the current revision. The program must reload or restart the application and complete its health check, not merely submit an asynchronous operation:

```json
{
  "deliveries": {
    "cred-pg-main": {
      "format": "env",
      "path": "/etc/jumpserver-pam/deliveries/database.env",
      "fields": {
        "DB_USER": "username",
        "DB_PASSWORD": "secret"
      },
      "owner": "order-service",
      "mode": "0600",
      "apply": ["/usr/local/sbin/apply-order-service"],
      "timeout": 120,
      "confirmation": "apply"
    }
  }
}
```

Supported source fields are `key`, `revision`, `asset_id`, `address`, `account_id`, `username`, `secret_type`, and `secret`; env values cannot contain NUL or newline. Delivery paths must be below a root-owned directory that is not group/world writable, with no symlink in the path. The apply program must be a root-owned absolute regular file, not a symlink or group/world writable. It runs as an argument list without a shell, and receives no secret in arguments, environment or logs. It reads `JMS_PAM_EVENT` (`published` or `revoked`), `JMS_PAM_CREDENTIAL_KEY`, `JMS_PAM_REVISION`, and `JMS_PAM_CREDENTIAL_FILE`. On revocation the target file has already been removed; a non-zero result is retried. `/var/lib/jumpserver-pam/delivery-state.json` preserves pending work across apply failures, restarts and confirmation failures without confirming early or rerunning an apply that already succeeded.

Without `deliveries`, or with `confirmation: manual`, the existing file and CLI/HTTP confirmation flow remains unchanged. Delivery rules and programs are local host configuration; JumpServer does not remotely distribute executable commands.

## Optional event notifications

Reinstallation with matching local settings verifies and reuses the existing Agent identity and preserves confirmation state, then explicitly restarts and checks the service. It does not submit a registration token or replace a same-name identity. After an uncertain registration response or local identity-save failure, check the server record first. Restore the original identity file where possible; otherwise review/remove only an unused instance, or choose a new instance ID and token. Do not overwrite an active instance. Failed identity checks preserve the existing configuration.

Enable event notifications on the client access configuration. SDK applications register a Python callback; Agent configurations specify an application HTTP(S) URL. Notifications are independent of credential retrieval and never replace applied-version confirmation.

```python
client = JumpServerPAMClient.from_config('jms-pam.json')

def on_event(event):
    application_event_queue.put(event)  # Your application's own queue/handler.

listener = client.start_events(handler=on_event)
# Continue running your application. On credential.published, fetch, check the
# version, reload connections, then confirm_applied(credential).
# At application shutdown: client.close()
```

Returning from the callback means delivered; raising an exception means failed. Keep callbacks short (claims expire after 60 seconds). Inspect `listener.last_error` for connection errors. `client.stop_events()` stops notifications without stopping credential retrieval. Each instance receives its own delivery; deduplicate by `event_id + client_id` (the globally unique instance UUID, unlike the display name `instance_id`).

Agent uses the same worker and POSTs JSON without authentication headers or redirects. Only 2xx responses count as delivered. This version targets trusted local execution environments, not publicly exposed endpoints. After changing the Agent URL, update its local configuration and restart it without re-registering its identity. Before delivering `credential.published`, Agent writes that exact revision to the local credential file. Superseded revisions fail delivery rather than being silently replaced. Confirm the actual revision using `--revision` or `POST /v1/confirm` with `{"key":"cred-pg-main","revision":2}`; key-only confirmation is no longer supported.

Event codes: `credential.published`, `credential.unavailable` (single-account change in progress), `rotation.failed`, and `access.revoked`. If JumpServer rejects authentication/access, the listener emits one local `access.stopped` event with `origin: client` and stops. Disabled identities cannot report results or fetch additional events.

JumpServer schedules at most five attempts, with 5/15/30/60-second retry delays and a ten-minute delivery deadline. Clients resume unexpired deliveries after reconnecting and retry result reports before invoking another callback. No secrets or application response bodies are sent in event/audit payloads. Delivery, credential retrieval and applied-version confirmation are distinct audit events. The old call-record UI/query API is retired (historical rows retained); legacy account-secret compatibility is unchanged.
