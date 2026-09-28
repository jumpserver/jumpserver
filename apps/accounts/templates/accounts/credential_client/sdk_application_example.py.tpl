from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


def apply_credential(response):
    # Replace this function with your application's connection update:
    # build and verify a new connection, switch to it, then release the old one.
    # Never write response.Account.Secret or authentication headers to logs.
    raise NotImplementedError('Implement the application connection update first')


def restart_application():
    # Implement restart and its health check, then return only after it succeeds.
    raise NotImplementedError('Implement the application restart first')


def handle_command(client, event):
    if event['event'] == 'application.restart.requested':
        restart_application()
    elif event['event'] == 'credential.switch.requested':
        response = client.GetCredential(models.GetCredentialRequest(Key=event['credential_key']))
        if response.Revision != event['revision'] or response.Account.Id != event['account_id']:
            raise ValueError('Requested account version is superseded')
        apply_credential(response)
        client.ConfirmCredential(models.ConfirmCredentialRequest(
            Key=response.Key, Revision=response.Revision, AccountId=response.Account.Id,
        ))
    else:
        raise ValueError('Unsupported application command')


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    for event in client.WatchCredentialEvents():
        if event.get('command_id'):
            try:
                client.ExecuteApplicationCommand(event, lambda command: handle_command(client, command))
            except Exception:
                pass  # Reported as failed; never log credentials or authentication headers.
            continue
        if event.get('event') == 'snapshot':
            updates = event.get('credentials', [])
            # Remove cached credentials absent from the new snapshot.
        elif event.get('event') == 'credential.updated':
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get('credential_key') or update.get('key')
            if not key:
                continue
            subscription = update.get('credential_mode') == 'subscription'
            if subscription and not update.get('account_id'):
                continue  # The server follows this event with an updated snapshot.
            response = client.GetCredential(models.GetCredentialRequest(Key=key))
            apply_credential(response)
            if not subscription:
                client.ConfirmCredential(models.ConfirmCredentialRequest(
                    Key=response.Key, Revision=response.Revision,
                    AccountId=response.Account.Id,
                ))
