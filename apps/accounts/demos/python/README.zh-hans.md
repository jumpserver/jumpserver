# JumpServer PAM Python SDK 与 Agent

应用可以使用 Python SDK 直接连接 JumpServer，也可以在应用主机部署 Linux Agent。客户端启动时获取轮换凭据，并通过签名认证的凭据事件流 WebSocket 接收订阅账号快照和后续更新；`credential.updated`、重连快照中的新版本以及管理员手动发送的账号切换请求会触发取密。

## 手动发起策略新周期

在凭据策略详情的“基本设置”或“事件接收”中点击“发起新周期”。发起后会打开新周期的时间线：

- 凭据变更订阅：为当前有应用授权的订阅账号重新发布 `credential.updated`，共用一个新的 `operation_id`。密码和版本不变，不生成改密开始、成功或失败事件。SDK 按事件 key 获取当前凭据；Agent 收到更新通知后也会重新取密，同版本不重复交付或重启服务。回执仅表示收到通知。离线客户端重连时通过快照获取当前凭据。
- 账号轮换：上一周期完成或取消后，从准备阶段发起新的周期。应用对齐当前账号后，等待备用账号连续无取密流量达到配置时长（默认 7 天），再由管理员发起切换。准备、切换与改密共用一个周期。

管理 API：`POST /api/v1/accounts/application-credentials/<policy-id>/start-cycle/`，需要策略修改权限，返回 `credential` 和 `cycle_id`。策略停用、轮换未结束时不能发起新周期；订阅账号正在改密时须等待改密结束再重新发布。

## 手动发送应用事件

在应用列表的“更多 > 发送事件”，或应用详情的“事件处理 > 发送事件”中，选择事件类型、目标连接实例和有效期。

- `credential.switch.requested`：要求应用切换到策略当前发布的账号和版本。该请求不会更换策略的发布账号；更换发布账号应在轮换策略中操作。应用取密后必须校验请求中的账号和版本，完成连接切换并调用 `ConfirmCredential`，再回报成功。
- `application.restart.requested`：SDK 应用调用自己实现的重启处理函数，并在健康检查成功后回报结果。Agent 仅支持接入时配置为 EnvironmentFile + restart 的 systemd 服务，先重启，再检查服务状态。

WebSocket 的 `received` 回执表示收到请求，不表示执行成功。SDK 的 `ExecuteApplicationCommand(event, handler)` 会先向 Core 申请执行，只有 `accepted: true` 才调用处理函数；重复投递不会再次执行。处理函数正常返回后报告成功，异常则报告失败。应用自行负责处理函数中的业务幂等和健康检查。Agent 的账号切换请求在应用确认实际使用版本后才报告成功。

离线实例可在有效期内重新连接接收请求。无法使用 WebSocket 的 API 应用也可通过 AK/SK 签名轮询，使用固定的 `instance_id`；首次轮询会登记实例，之后管理员便可选择该实例发送事件：

1. `GET /api/v1/accounts/credential-client/commands/?instance_id=<instance-id>` 获取待处理请求（SDK 对应 `ListApplicationCommands()`）。使用与凭据客户端相同的签名头，协议版本为 1。
2. `POST /api/v1/accounts/credential-client/command-result/`，提交 `instance_id`、`command_id` 和 `status: running`。只有响应 `accepted: true` 才执行。
3. 执行结束后向同一接口提交 `status: success` 或 `status: failed`；失败可附带不含敏感数据的 `error_code`。SDK 对应 `ReportApplicationCommandResult()`。

请求超过有效期会显示超时，不能再申请执行。已申请执行的重启若因进程退出而无法回报，需检查应用状态后由管理员决定是否重新发送。普通旧取密 API 保持不变，仅调用取密接口不会接收手动事件。

## 选择接入方式

| 方式 | 适用场景 | 应用需要完成的工作 |
| --- | --- | --- |
| Python SDK | 应用可以修改 Python 代码并直接访问 JumpServer | 监听事件、拉取变化的凭据、切换连接并确认版本 |
| Linux Agent | 不希望应用保存 JumpServer 密钥，或需要文件、EnvironmentFile、Unix Socket 交付 | 加载并验证 Agent 交付的凭据，再确认实际使用的版本 |

<!-- agent-doc:start -->

## Linux Agent 完整接入

下面以“双账号交替轮换 + JSON 文件交付”为例。从准备数据开始，完成 Agent 安装、首次取密和一次完整的凭据轮换。

### 接入前准备

确认以下条件已经满足：

- Agent 主机使用 systemd，已安装 Python 3.9 或更高版本，并能访问 JumpServer Core 地址。
- 你可以在 Agent 主机使用 `sudo`，而且应用运行用户已经存在。
- 目标资产和账号可以从 JumpServer 正常连接。
- 应用与 Agent 位于同一主机；容器化应用需要共享 Agent 的 Unix Socket 目录，并使用匹配的应用用户 UID。

### 创建凭据策略

1. 进入“PAM 集成 > 凭据策略”，创建一个凭据策略。
2. 模式选择“双账号交替轮换”。
3. 选择初始账号、交替账号和一个或多个绑定应用，然后保存。
4. 记下凭据详情中的“接入标识”，后续命令使用的是这个值，而不是凭据名称。

### 授权应用账号

1. 进入“应用管理”，创建或打开目标应用。
2. 在应用详情的“账号授权”页面授权凭据策略使用的资产账号。
3. 使用交替轮换时，两个账号都必须授权。

应用接入不会自动增加账号授权。授权不完整时，Agent 无法获取凭据。

### 使用应用接入向导

1. 打开应用详情的“接入与连接实例”，点击“接入向导”。
2. 选择“Agent 接入”。所有绑定到应用的有效策略会自动加入，无需选择策略。
3. 填写应用运行用户和安装路径。默认安装路径为 `/opt/jumpserver-pam`。
4. 选择凭据交付方式，生成并下载接入材料。

| 交付方式 | Agent 行为 | 应用行为 |
| --- | --- | --- |
| JSON 文件 | 每个凭据写入一个 `<credential-key>.json` 文件 | 监听或定时读取文件，验证新连接后确认版本 |
| systemd EnvironmentFile | 写入 `<credential-key>.env`，然后执行配置的 `reload` 或 `restart` | systemd 服务引用该文件，启动或重载成功并验证连接后确认版本 |
| Unix Socket | 不生成业务凭据文件，通过本机 Socket 返回当前缓存 | 调用本机取密接口，验证新连接后调用确认接口 |

EnvironmentFile 模式要求应用的 systemd unit 提前引用对应文件，例如：

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

默认选择 `restart`。只有应用的 reload 处理程序会主动重新读取 EnvironmentFile 时才选择 `reload`；systemd reload 本身不会把新环境变量重新注入已运行进程。

`<configuration-id>` 可以在下载的引导文件中查看 `configuration_id` 字段。安装路径、应用用户、Socket 路径以及可操作的 systemd 服务会在安装时固定；扩大这些权限需要重新安装 Agent。

### 安装 Agent

1. 准备使用 systemd、Python 3.9+ 且已创建应用运行用户的 Linux 应用主机。
2. 将下载的 `jms_pam_agent.json` 放到主机，在文件所在目录运行向导中的安装命令。Agent 使用应用的 AK/SK 签名访问 API 与 WebSocket。
3. 回到应用的“接入与连接实例”，确认实例显示“在线”。

下载文件包含应用的 AK/SK，请限制文件访问权限，安装后删除下载的引导文件。Agent 安装后的配置文件仅允许 root 读取。

安装后检查服务：

```bash
sudo systemctl status jms-pam-agent-<configuration-id>.service --no-pager
```

使用向导中填写的应用运行用户检查本机接口：

```bash
sudo -u <app-user> curl --fail --silent --show-error \
  --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/health
```

正常响应示例：

```json
{"status":"ok","sync_status":"success"}
```

回到应用详情的“接入与连接实例”查看连接状态。Agent 启动时立即同步，收到凭据事件时实时同步，并保留低频全量对账作为断线兜底。

### 让应用使用并确认凭据

JSON 文件默认位于：

```text
/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json
```

文件包含固定字段：`key`、`revision`、资产信息、账号信息、`username`、`secret_type` 和 `secret`。应用应按以下顺序处理：

1. 读取完整文件，并比较 `revision` 是否变化。
2. 使用新凭据创建连接并执行真实的轻量验证，例如数据库 `SELECT 1`。
3. 原子切换连接池或应用配置。
4. 只有切换成功后，才确认应用实际使用的版本。

```bash
sudo -u <app-user> /opt/jumpserver-pam/venv/bin/jms-pam-agent confirm \
  <credential-key> \
  --revision <revision> \
  --socket /run/jumpserver-pam/<configuration-id>/agent.sock
```

生产应用应在真实连接验证和切换成功后自动调用本机确认接口；上述命令主要用于调试和人工兜底。Agent 会先在本机持久化确认状态，再通过确认接口上报；Core 暂时不可达时会在后续对账中重试。

成功响应包含 `key`、`revision`、`account_id` 和 `status: confirmed`（Core 暂不可达时为 `pending`）。确认接口是幂等的。不要因为文件写入、服务重启或事件送达就自动确认。

## 完整示例：完成一次凭据轮换

下面继续使用已经接入的双账号交替轮换策略。

1. 进入“PAM 集成 > 凭据策略”，打开目标策略并点击“发起新周期”。所有应用对齐到当前账号后，观察备用账号连续无取密流量的时长（默认 7 天，可配置）。达标会通知发起管理员，再由管理员点击“开始轮换”。
2. JumpServer 发布另一个账号并发送 `credential.updated`。
3. 每个启用的 Agent 实例取密并交付；应用切换成功后确认该 revision。
4. 所有参与实例确认后，为被替换的账号创建并执行改密任务。
5. 检查改密结果。轮换完成后另一个账号继续作为当前账号；下一轮按相反方向切换。

不要复制文档示例中的 revision。必须确认应用实际加载的 revision；确认旧版本会被 Agent 拒绝。

如果改密在真正修改密码前失败，修复网络、端口或执行环境后点击“重试”。如果状态为“密码需要核验”，先在“改密结果”中测试候选密码，再根据结果继续处理。

任一启用实例的 WebSocket 离线或未确认目标 revision，都会阻止改密。确认每个应用实例都有稳定且唯一的实例标识。

## Agent 本机接口

Agent 只在受保护的 Unix Socket 上提供本机接口，不监听 TCP 端口。Socket 默认属于向导中填写的应用运行用户，权限为 `0600`。

### 健康检查

```bash
curl --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/health
```

- `status: ok`：Agent 允许本机取密。
- `status: denied`：Agent 身份已禁用或协议版本不受支持，本机取密会被拒绝。
- `sync_status: success`：最近一次配置与凭据同步成功。

### 获取凭据

Unix Socket 交付模式下，应用按凭据接入标识获取当前缓存：

```bash
curl --fail --silent --show-error \
  --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/credentials/<credential-key>
```

响应包含密码。不要把响应、请求调试信息或凭据文件写入日志。

### 确认凭据

只有双账号交替轮换需要确认。生产应用应在新凭据通过真实连接验证并完成切换后调用本机接口。随 Agent 安装的命令用于调试和人工兜底，应用不需要保存 Agent 密钥：

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm \
  <credential-key> \
  --revision <revision> \
  --socket /run/jumpserver-pam/<configuration-id>/agent.sock
```

本机接口等价请求为：

```http
POST /v1/confirm
Content-Type: application/json

{"key":"<credential-key>","revision":<revision>}
```

本机接口成功即表示确认状态已安全落盘；Agent 会通过确认接口上报，并在后续对账中重试。Core 短暂不可达不影响应用完成本机确认。

## Agent 常用命令

```bash
# 查看状态
sudo systemctl status jms-pam-agent-<configuration-id>.service --no-pager

# 查看最近日志
sudo journalctl -u jms-pam-agent-<configuration-id>.service -n 100 --no-pager

# 持续查看日志
sudo journalctl -u jms-pam-agent-<configuration-id>.service -f

# 重启；启动后会立即执行一次同步
sudo systemctl restart jms-pam-agent-<configuration-id>.service

# 升级 Agent 后重启
sudo /opt/jumpserver-pam/venv/bin/pip install --upgrade jms-pam
sudo systemctl restart jms-pam-agent-<configuration-id>.service
```

网络暂时不可达时，Agent 会继续保留最后一次有效缓存并重试。应用或实例被禁用、授权被撤销或 Core 返回升级要求时，Agent 会停止通过 Socket 返回密码，但不会自动删除已经写入的文件。

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Python SDK 完整接入

仓库另附两个可独立运行的文件配置 Demo：`file_apps.subscription` 和 `file_apps.rotation`。它们使用本节生成的 SDK 配置，接收事件后更新本地 JSON；运行命令和轮换确认条件见 `apps/accounts/demos/python/file_apps/README.zh-hans.md`。

SDK 使用应用的 AK/SK，自动接收所有绑定到应用的有效策略。一条连接可同时处理订阅和轮换，接入向导提供按策略模式处理的通用示例。策略绑定变化自动生效。

### 接入前准备

1. 在“PAM 集成 > 凭据策略”创建“凭据变更订阅”或“账号轮换”策略并绑定应用。订阅策略明确选择要通知的账号；账号轮换当前选择同一资产上的两个账号。
2. 创建或打开目标应用，在“账号授权”页面授权应用可使用的资产账号。交替轮换必须授权策略中的两个账号。
3. 打开应用详情的“接入与连接实例”，点击“接入向导”，选择“SDK 接入”。
4. 生成并下载 `jms_pam_config.py`，使用向导中的示例代码。无需配置 ID 或策略列表。

每个应用进程或连接池都必须使用稳定且唯一的 `instance_id`。重新部署同一实例时应复用原标识，不同实例不能共享标识。

### 安装与配置

SDK 需要 Python 3.9 及以上。使用应用实际运行的 Python 或虚拟环境从 PyPI 安装：

```bash
python3 -m pip install --upgrade jms-pam
```

将 `jms_pam_config.py` 放入应用可以导入的位置。该文件包含应用身份信息，不要提交到代码仓库或输出到日志。

### 凭据变更订阅

管理员可以从应用管理查询账号 ID。已授权账号可以直接按 ID 取密：

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


with credential_client.CredentialClient(
    cred, instance_id='order-service-node-1', profile=profile,
) as client:
    response = client.GetCredential(models.GetCredentialRequest(
        AccountId='<account-id>',
    ))
    password = response.Account.Secret
```

常驻应用监听凭据事件流；首次连接和重连快照也会提供当前账号：

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


def fetch_credential(client, account_id):
    response = client.GetCredential(models.GetCredentialRequest(AccountId=account_id))
    address = response.Asset.Address
    username = response.Account.Username
    secret_type = response.Account.SecretType
    secret = response.Account.Secret
    # 使用新凭据更新应用连接；不要记录 secret。


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
```

订阅不需要 `credential_keys` 或 `ConfirmCredential`。生命周期事件只用于观察状态，不触发取密。

### 双账号交替轮换

事件快照提供每条轮换策略的唯一 Key。收到首次快照时获取当前账号，收到更新或重连快照后再次取密；只有应用验证新连接并切换成功后才能确认：

```python
from jms_pam.credential.v1 import credential_client, models
from jms_pam_config import cred, profile


def switch_credential(client, key):
    response = client.GetCredential(models.GetCredentialRequest(Key=key))
    # 使用返回的资产、账号和密码建立连接，验证成功后切换应用连接池。
    client.ConfirmCredential(models.ConfirmCredentialRequest(
        Key=response.Key,
        Revision=response.Revision,
        AccountId=response.Account.Id,
    ))


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
            key = update.get('credential_key') or update.get('key')
            if key and update.get('credential_mode') == 'alternating_rotation':
                switch_credential(client, key)
```

`Account.Secret` 是密码或密钥内容，具体类型由 `Account.SecretType` 标识。不要把密码或认证请求头写入日志。

### 完成一次凭据轮换

1. 在“PAM 集成 > 凭据策略”中打开目标策略并点击“发起新周期”。应用确认当前账号后，等待备用账号连续无取密流量达到配置时长（默认 7 天）；收到就绪通知后，由管理员点击“开始轮换”。
2. JumpServer 切换当前生效账号并发送 `credential.updated`。
3. 应用按事件中的 key 调用 `GetCredential`，使用新账号建立并验证连接，切换成功后调用 `ConfirmCredential`；生命周期事件只记录状态，不触发取密。
4. 所有参与实例确认后点击“继续轮换”，创建并执行原账号的改密任务。
5. 检查改密结果；成功后轮换完成，当前账号保持不变，下一轮按相反方向切换。

### SDK 常用方法

同步客户端提供以下常用方法：

- `GetCredential`：交替轮换使用 `Key`，凭据变更订阅使用 `AccountId`，两者必须且只能提供一个。
- `ConfirmCredential`：仅用于交替轮换，确认应用已经验证并使用指定 revision。
- `WatchCredentialEvents`：阻塞监听凭据事件和重连快照。

SDK 在将业务事件交给调用方前自动尽力发送接收回执。回执仅表示 SDK/Agent 已读取该事件，不表示已取密或应用凭据，也不能代替 `ConfirmCredential`；回执发送失败不影响事件处理。已有 SDK/Agent 部署需要更新并重启后才能上报回执。重连快照用于恢复当前凭据版本，不会重放历史事件或补报历史回执。

连接在线状态由 WebSocket Ping/Pong 维护，不再提供 HTTP 心跳接口。应用只需保留低频版本对账作为恢复路径。

HTTP、鉴权、网络和响应解析错误统一抛出 `jms_pam.common.exception.JumpServerPAMSDKException`。业务重试边界可以读取 `code`、`status_code`、`detail` 和 `original_error`。日志中不要记录凭据或认证请求头。

<!-- sdk-doc:end -->
