from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    # 使用 credential.asset.address 和 credential.account 更新应用连接。
    # 不要把 credential.account.secret 或认证请求头写入日志。
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
