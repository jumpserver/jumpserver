from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


def fetch_credential(client, account_id):
    response = client.GetCredential(models.GetCredentialRequest(AccountId=account_id))

    address = response.Asset.Address
    username = response.Account.Username
    secret_type = response.Account.SecretType
    secret = response.Account.Secret

    # 使用 address、username 和 secret 更新应用连接。
    # 不要把 secret 或认证请求头写入日志。


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    for event in client.WatchCredentialEvents():
        if event.get('event') == 'snapshot':
            updates = event.get('credentials', [])
        elif event.get('event') == 'credential.updated':
            updates = [event]
        else:
            continue
        for update in updates:
            account_id = update.get('account_id')
            if update.get('credential_mode') == 'subscription' and account_id:
                fetch_credential(client, account_id)
