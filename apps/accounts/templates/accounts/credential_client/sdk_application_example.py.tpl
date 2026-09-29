from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(response):
    # Replace this function with your application's connection update:
    # build and verify a new connection, switch to it, then release the old one.
    # Never write response.account.secret or authentication headers to logs.
    raise NotImplementedError("Implement the application connection update first")


def restart_application():
    # Implement restart and its health check, then return only after it succeeds.
    raise NotImplementedError("Implement the application restart first")


def handle_command(client, event):
    if event["event"] == "application.restart.requested":
        restart_application()
    elif event["event"] == "credential.switch.requested":
        response = client.get_credential(key=event["credential_key"])
        if (
            response.revision != event["revision"]
            or response.account.id != event["account_id"]
        ):
            raise ValueError("Requested account version is superseded")
        apply_credential(response)
        client.confirm_credential(
            key=response.key, revision=response.revision, account_id=response.account.id
        )
    else:
        raise ValueError("Unsupported application command")


with Client(instance_id="order-service-node-1", **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("command_id"):
            try:
                client.execute_application_command(
                    event, lambda command: handle_command(client, command)
                )
            except Exception:
                pass  # Reported as failed; never log credentials or authentication headers.
            continue
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
            # Remove cached credentials absent from the new snapshot.
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get("credential_key") or update.get("key")
            if not key:
                continue
            subscription = update.get("credential_mode") == "subscription"
            if subscription and not update.get("account_id"):
                continue  # The server follows this event with an updated snapshot.
            response = client.get_credential(key=key)
            apply_credential(response)
            if not subscription:
                client.confirm_credential(
                    key=response.key,
                    revision=response.revision,
                    account_id=response.account.id,
                )
