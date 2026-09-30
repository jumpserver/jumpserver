from jms_pam import Client
from jms_pam_config import client_options, confirmation_keys, credential_keys


def apply_credential(credential):
    # Build and verify a new connection, switch the application to it,
    # then release the old connection. Never log credential.account.secret.
    raise NotImplementedError("Implement the application connection update first")


def switch_credential(client, key):
    response = client.get_credential(key=key, allow_local_fallback=False)
    apply_credential(response)

    if key in confirmation_keys:
        client.confirm_credential(
            key=response.key, revision=response.revision, account_id=response.account.id
        )


with Client(instance_id="order-service-node-1", **client_options) as client:
    for key in credential_keys:
        switch_credential(client, key)
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get("credential_key") or update.get("key")
            if key in credential_keys:
                switch_credential(client, key)
