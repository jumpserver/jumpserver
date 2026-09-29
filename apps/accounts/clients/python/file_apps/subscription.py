"""Demo application: subscribe to account secret changes and rewrite local JSON."""

import logging
import time

from jms_pam import Client

from .common import arguments, credential_data, load_local, load_sdk_config, save_local

LOG = logging.getLogger(__name__)
KIND = "subscription"


def update_account(client, output, account_id, expected_revision=None):
    current = load_local(output, KIND)
    existing = current["credentials"].get(account_id)
    if (
        expected_revision is not None
        and existing
        and existing["revision"] >= expected_revision
    ):
        return False
    response = client.get_credential(account_id=account_id)
    if existing and existing["revision"] >= response.revision:
        return False
    current["credentials"][account_id] = credential_data(response)
    save_local(output, current)
    LOG.info("Updated account %s to revision %s", account_id, response.revision)
    return True


def handle_event(client, output, event):
    if event.get("event") == "snapshot":
        subscriptions = {
            item["account_id"]: item["revision"]
            for item in event.get("credentials", [])
            if item.get("credential_mode") == KIND and item.get("account_id")
        }
        for account_id, revision in subscriptions.items():
            update_account(client, output, account_id, revision)
        current = load_local(output, KIND)
        stale = set(current["credentials"]) - set(subscriptions)
        if stale:
            for account_id in stale:
                del current["credentials"][account_id]
            save_local(output, current)
            LOG.info(
                "Removed %s credentials absent from the current snapshot", len(stale)
            )
    elif (
        event.get("event") == "credential.updated"
        and event.get("credential_mode") == KIND
    ):
        account_id = event.get("account_id")
        if account_id:
            update_account(client, output, account_id, event.get("revision"))
    elif event.get("event") == "credential.revoked":
        policy_key = event.get("credential_key")
        if policy_key:
            current = load_local(output, KIND)
            stale = [
                account_id
                for account_id, item in current["credentials"].items()
                if item["key"].partition(":")[0] == policy_key
            ]
            if stale:
                for account_id in stale:
                    del current["credentials"][account_id]
                save_local(output, current)
                LOG.info("Removed %s revoked credentials", len(stale))
    return event.get("event") == "configuration.updated"


def main():
    args = arguments("JumpServer credential change subscription demo")
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    config = load_sdk_config(args.config)
    while True:
        try:
            with Client(
                instance_id=args.instance_id, **config.client_options
            ) as client:
                stream = client.watch_credential_events()
                try:
                    for event in stream:
                        if handle_event(client, args.output, event):
                            break  # Reconnect to receive the authoritative configuration snapshot.
                finally:
                    stream.close()
        except KeyboardInterrupt:
            break
        except Exception as error:
            LOG.error(
                "Subscription processing failed (%s); reconnecting",
                type(error).__name__,
            )
            time.sleep(5)


if __name__ == "__main__":
    main()
