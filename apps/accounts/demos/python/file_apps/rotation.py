"""Demo application: apply alternating-account rotations to local JSON."""
import logging
import time

from jms_pam.credential.v1 import credential_client, models

from .common import (
    arguments, credential_data, load_local, load_sdk_config, save_local, verify_local,
)


LOG = logging.getLogger(__name__)
KIND = 'alternating_rotation'


def update_credential(client, output, key, confirm=False):
    response = client.GetCredential(models.GetCredentialRequest(Key=key))
    current = load_local(output, KIND)
    existing = current['credentials'].get(key)
    if not existing or existing['revision'] < response.Revision:
        current['credentials'][key] = credential_data(response)
        save_local(output, current)
        LOG.info('Updated policy %s to revision %s', key, response.Revision)
    elif existing['revision'] > response.Revision:
        raise ValueError('JumpServer returned an older credential revision')

    # This file is the entire state of the demo application. A real application
    # must validate and switch its live connection before reporting success.
    verify_local(output, KIND, key, response)
    if confirm:
        client.ConfirmCredential(models.ConfirmCredentialRequest(
            Key=response.Key, Revision=response.Revision, AccountId=response.Account.Id,
        ))
        LOG.info('Confirmed policy %s revision %s', key, response.Revision)


def handle_event(client, output, event, keys, confirm=False):
    if event.get('event') == 'snapshot':
        updates = event.get('credentials', [])
    elif event.get('event') == 'credential.updated':
        updates = [event]
    elif event.get('event') == 'credential.revoked':
        key = event.get('credential_key')
        if key and (keys is None or key in keys):
            current = load_local(output, KIND)
            if current['credentials'].pop(key, None):
                save_local(output, current)
                LOG.info('Removed revoked policy %s', key)
        return False
    else:
        return event.get('event') == 'configuration.updated'
    for update in updates:
        if update.get('credential_mode') != KIND:
            continue
        key = update.get('credential_key') or update.get('key')
        if key and (keys is None or key in keys):
            update_credential(client, output, key, confirm=confirm)
    if event.get('event') == 'snapshot':
        present = {
            item.get('key') for item in updates if item.get('credential_mode') == KIND
        }
        current = load_local(output, KIND)
        stale = set(current['credentials']) - present
        if stale:
            for key in stale:
                del current['credentials'][key]
            save_local(output, current)
            LOG.info('Removed %s policies absent from the current snapshot', len(stale))
    return False


def main():
    args = arguments('JumpServer alternating credential rotation demo', rotation=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    config = load_sdk_config(args.config)
    keys = set(config.credential_keys) if hasattr(config, 'credential_keys') else None
    if keys == set():
        raise ValueError('The SDK configuration has no alternating rotation policy keys')
    while True:
        try:
            with credential_client.CredentialClient(
                config.cred, instance_id=args.instance_id, profile=config.profile,
            ) as client:
                stream = client.WatchCredentialEvents()
                try:
                    for event in stream:
                        if handle_event(
                            client, args.output, event, keys, confirm=args.confirm_file_only,
                        ):
                            break  # Reconnect to receive the authoritative configuration snapshot.
                finally:
                    stream.close()
        except KeyboardInterrupt:
            break
        except Exception as error:
            LOG.error('Rotation processing failed (%s); reconnecting', type(error).__name__)
            time.sleep(5)


if __name__ == '__main__':
    main()
