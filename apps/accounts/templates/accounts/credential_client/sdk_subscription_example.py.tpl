from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    # Use credential.asset.address and credential.account to update connections.
    # Never write credential.account.secret or authentication headers to logs.
    raise NotImplementedError("Implement the application connection update first")


def fetch_credential(client, account_id):
    credential = client.get_credential(account_id=account_id)
    apply_credential(credential)


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
