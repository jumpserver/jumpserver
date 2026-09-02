# JumpServer PAM Python SDK and Agent

Install with Python 3.9 or later:

```bash
pip install ./apps/accounts/demos/python
```

Fetch a credential by its immutable key, replace and verify the application's connection pool, release the old pool, and then confirm the applied revision:

```python
from jms_pam import JumpServerPAMClient

client = JumpServerPAMClient(
    endpoint='https://jms.example.com',
    app_id='application-id',
    app_secret='application-secret',
    org_id='organization-id',
)

credential = client.get_credential('cred-pg-main')
new_pool = create_pool(username=credential.username, password=credential.secret)
new_pool.check_connection()
old_pool.close()
client.confirm_applied(credential)
```

The SDK reports a heartbeat every 30 seconds. Set `JMS_PAM_INSTANCE_ID` when an application runs more than one instance.

For Linux Agent installation, generate a one-time registration token in the application detail page and run:

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
jms-pam-agent confirm cred-pg-main
```
