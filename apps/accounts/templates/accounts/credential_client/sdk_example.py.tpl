import time

from jms_pam.common.exception import JumpServerPAMSDKException
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile, credential_keys


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    applied = {}
    while True:
        for key in credential_keys:
            try:
                response = client.GetCredential(models.GetCredentialRequest(Key=key))

                # Build and verify a new connection with response.Account.Username
                # and response.Account.Secret, then release the old connection.

                client.ConfirmCredential(models.ConfirmCredentialRequest(
                    Key=response.Key,
                    Revision=response.Revision,
                    AccountId=response.Account.Id,
                ))
                applied[key] = models.CredentialState(
                    Key=response.Key,
                    Revision=response.Revision,
                    AccountId=response.Account.Id,
                )
            except JumpServerPAMSDKException as error:
                print(error)

        client.Heartbeat(models.HeartbeatRequest(Credentials=list(applied.values())))
        time.sleep(30)
