from jms_pam import Client
from jms_pam_config import client_options, instance_id


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
        response = client.get_credential(key=event["credential_key"], allow_local_fallback=False)
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


class ApplicationClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}
        self.credential_modes = {}

    def on_event(self, event):
        if event.get("command_id"):
            self.execute_application_command(
                event, lambda command: handle_command(self, command)
            )
        elif event.get("event") == "snapshot":
            self.credential_modes = {
                item["key"]: item["credential_mode"]
                for item in event.get("credentials", [])
            }
            for key in self.credentials.keys() - self.credential_modes.keys():
                # Also release the application's connections for the removed key.
                del self.credentials[key]
        elif event.get("event") == "credential.updated":
            key = event.get("credential_key") or event.get("key")
            if key:
                self.credential_modes[key] = event.get("credential_mode")

    def on_credential_changed(self, credential):
        apply_credential(credential)
        if self.credential_modes.get(credential.key) == "alternating_rotation":
            self.confirm_credential(
                key=credential.key,
                revision=credential.revision,
                account_id=credential.account.id,
            )
        self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        key = event.get("credential_key")
        self.credentials.pop(key, None)
        # Release affected connections. The following snapshot reconciles all keys.


with ApplicationClient(instance_id=instance_id, **client_options) as client:
    client.watch_events()
