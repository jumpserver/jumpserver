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

Create a client access configuration in the application's Client Access tab, select credentials, and download `jms-pam.json`. It includes the endpoint, application credentials, organization and configuration ID. Protect this file as a secret. Fetch periodically while the application runs; confirm only after successfully applying the returned version. The SDK reports a heartbeat every 30 seconds. Set a distinct `JMS_PAM_INSTANCE_ID` for replicas sharing a hostname.

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
jms-pam-agent confirm cred-pg-main
```
