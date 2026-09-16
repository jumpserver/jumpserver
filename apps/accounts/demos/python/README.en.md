# JumpServer PAM Python SDK and Agent

## Install

Python 3.9 or later is required. Install from PyPI with the Python interpreter or virtual environment used by the application:

```bash
python3 -m pip install --upgrade jms-pam
```

After installation, generate and download client materials from the application's Client Access page.

## SDK integration

Download `jms_pam_config.py` and protect it as a secret. It exports `cred`, `profile`, `credential_keys`, and `notification_enabled`. Each process or connection pool must pass a stable, unique `instance_id` when creating its client.

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
```

The synchronous client provides `GetCredential`, `ConfirmCredential`, `Heartbeat`, `SubscribeEvents`, `PollEvents`, and `ReportEvent`. It starts no background threads. Schedule heartbeats, polling, and retries in the application:

```python
state = models.CredentialState(
    Key=response.Key,
    Revision=response.Revision,
    AccountId=response.Account.Id,
)
client.Heartbeat(models.HeartbeatRequest(Credentials=[state]))

client.SubscribeEvents(models.SubscribeEventsRequest(Enabled=True))
events = client.PollEvents(models.PollEventsRequest())
for event in events.Events:
    try:
        handle_event(event)
        report = models.ReportEventRequest(
            AttemptId=event.AttemptId,
            Result='success',
        )
    except Exception:
        report = models.ReportEventRequest(
            AttemptId=event.AttemptId,
            Result='failed',
            Reason='callback_failed',
        )
    client.ReportEvent(report)
```

All HTTP, authentication, network, and response errors are raised as `JumpServerPAMSDKException` from `jms_pam.common.exception`. Its `code`, `status_code`, `detail`, and `original_error` fields can be used at the application's retry boundary. Never log credentials or authentication headers.

## Linux Agent

The generated Agent command creates a virtual environment, installs the package, registers a single-use identity, and manages the systemd service. Registration material expires after ten minutes. The Agent writes credentials atomically to `/etc/jumpserver-pam/credentials.json` and listens for local confirmation only on `127.0.0.1:8081`.

After the application has loaded and verified a revision, confirm the exact version:

```bash
jms-pam-agent confirm cred-pg-main --revision 2
```

Managed delivery remains configured through local `deliveries` in `agent.json`. Delivery programs must be root-owned executable files, must complete application reload and health checking before returning success, and receive secrets only through the protected credential file. Event notification and credential confirmation remain separate operations.
