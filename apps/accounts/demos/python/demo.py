from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile, credential_keys


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    response = client.GetCredential(models.GetCredentialRequest(Key=credential_keys[0]))

    # 使用 response.Account.Username 和 response.Account.Secret 创建并验证新连接，
    # 再关闭旧连接池。成功后才确认应用已经使用这个版本。
    client.ConfirmCredential(models.ConfirmCredentialRequest(
        Key=response.Key,
        Revision=response.Revision,
        AccountId=response.Account.Id,
    ))
