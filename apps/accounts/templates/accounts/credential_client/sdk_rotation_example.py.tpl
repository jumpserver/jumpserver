from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import confirmation_keys, cred, credential_keys, profile


def switch_credential(client, key):
    response = client.GetCredential(models.GetCredentialRequest(Key=key))

    address = response.Asset.Address
    username = response.Account.Username
    secret_type = response.Account.SecretType
    secret = response.Account.Secret

    # Build and verify a new connection, switch the application to it,
    # then release the old connection. Never write secret to logs.

    if key in confirmation_keys:
        client.ConfirmCredential(models.ConfirmCredentialRequest(
            Key=response.Key,
            Revision=response.Revision,
            AccountId=response.Account.Id,
        ))


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    for key in credential_keys:
        switch_credential(client, key)
    for event in client.WatchCredentialEvents():
        if event.get('event') == 'snapshot':
            updates = event.get('credentials', [])
        elif event.get('event') == 'credential.updated':
            updates = [event]
        else:
            continue
        for update in updates:
            key = update.get('credential_key') or update.get('key')
            if key in credential_keys:
                switch_credential(client, key)
