# JumpServer PAM Python SDK 与 Agent

## Python SDK

环境要求：Python 3.9 及以上。

```bash
pip install ./apps/accounts/demos/python
```

应用在 JumpServer 的应用详情中获取应用 ID、应用密钥、组织 ID和凭据标识，然后按凭据标识读取当前账号：

```python
from jms_pam import JumpServerPAMClient

client = JumpServerPAMClient(
    endpoint='https://jms.example.com',
    app_id='应用 ID',
    app_secret='应用密钥',
    org_id='组织 ID',
)

credential = client.get_credential('cred-pg-main')

new_pool = create_pool(
    username=credential.username,
    password=credential.secret,
)
new_pool.check_connection()
old_pool.close()

client.confirm_applied(credential)
```

`get_credential()` 只表示应用拿到了新账号。应用成功建立新连接并释放旧连接后，必须调用 `confirm_applied()`。SDK 会自动每 30 秒上报一次心跳。

同一个应用有多个运行副本时，建议给每个副本设置稳定的实例标识：

```bash
export JMS_PAM_INSTANCE_ID=order-service-node-1
```

## Linux Agent

Agent 支持 Python 3、Linux 和 systemd。应用从 `/etc/jumpserver-pam/credentials.json` 读取当前账号，Agent 本地接口只监听 `127.0.0.1:8081`，不提供取密接口，也不使用本地认证。

在应用详情生成一次性注册令牌后执行：

```bash
sudo jms-pam-agent install \
  --endpoint https://jms.example.com \
  --token 一次性注册令牌 \
  --instance-id order-service-node-1 \
  --credential cred-pg-main \
  --app-user order-service
```

Agent 每 30 秒检查凭据版本并原子更新配置文件。应用重载、验证新连接并释放旧连接后执行：

```bash
jms-pam-agent confirm cred-pg-main
```

凭据文件示例：

```json
{
  "cred-pg-main": {
    "key": "cred-pg-main",
    "revision": 2,
    "asset": "pg-prod-01",
    "address": "10.0.0.10",
    "account": "account-b",
    "username": "account-b",
    "secret_type": "password",
    "secret": "******"
  }
}
```

配置文件权限为 `0600`，只保留当前版本，不生成密码历史或备份文件。
