# JumpServer PAM Python SDK 与 Agent

## 安装

SDK 需要 Python 3.9 及以上。使用应用实际运行的 Python 或虚拟环境从 PyPI 安装：

```bash
python3 -m pip install --upgrade jms-pam
```

安装完成后，在应用的「客户端接入」页面生成并下载接入材料。

## SDK 接入

下载 `jms_pam_config.py` 并按敏感材料保管。该文件导出 `cred`、`profile`、`credential_keys` 和 `notification_enabled`。每个进程或连接池创建客户端时，都必须传入稳定且唯一的 `instance_id`。

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile, credential_keys


with credential_client.CredentialClient(
    cred,
    instance_id='order-service-node-1',
    profile=profile,
) as client:
    response = client.GetCredential(
        models.GetCredentialRequest(Key=credential_keys[0])
    )

    new_pool = create_pool(
        username=response.Account.Username,
        password=response.Account.Secret,
    )
    new_pool.check_connection()
    old_pool.close()

    client.ConfirmCredential(models.ConfirmCredentialRequest(
        Key=response.Key,
        Revision=response.Revision,
        AccountId=response.Account.Id,
    ))
```

同步客户端提供 `GetCredential`、`ConfirmCredential`、`Heartbeat`、`SubscribeEvents`、`PollEvents` 和 `ReportEvent`。SDK 不启动后台线程，业务程序需要显式调度心跳、事件轮询和重试：

```python
state = models.CredentialState(
    Key=response.Key,
    Revision=response.Revision,
    AccountId=response.Account.Id,
)
client.Heartbeat(models.HeartbeatRequest(Credentials=[state]))

client.SubscribeEvents(models.SubscribeEventsRequest(Enabled=True))
events = client.PollEvents(models.PollEventsRequest())
for event in events.Events:
    try:
        handle_event(event)
        report = models.ReportEventRequest(
            AttemptId=event.AttemptId,
            Result='success',
        )
    except Exception:
        report = models.ReportEventRequest(
            AttemptId=event.AttemptId,
            Result='failed',
            Reason='callback_failed',
        )
    client.ReportEvent(report)
```

HTTP、鉴权、网络和响应解析错误统一抛出 `jms_pam.common.exception.JumpServerPAMSDKException`。业务重试边界可读取 `code`、`status_code`、`detail` 和 `original_error`。日志中不要记录凭据或认证请求头。

## Linux Agent

页面生成的 Agent 命令会创建虚拟环境、安装软件包、使用一次性身份注册，并管理 systemd 服务。注册材料有效期为十分钟。Agent 将凭据原子写入 `/etc/jumpserver-pam/credentials.json`，本地确认接口仅监听 `127.0.0.1:8081`。

应用加载并验证指定版本后，确认实际使用的版本：

```bash
jms-pam-agent confirm cred-pg-main --revision 2
```

托管交付继续通过 `agent.json` 的本地 `deliveries` 配置。生效程序必须由 root 所有，必须在返回成功前完成应用重载和健康检查，只能通过受保护的凭据文件读取密钥。事件通知与凭据确认仍是两个独立动作。
