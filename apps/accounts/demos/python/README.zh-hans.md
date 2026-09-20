# JumpServer PAM Python SDK 与 Agent

应用可以使用 Python SDK 直接连接 JumpServer，也可以在应用主机部署 Linux Agent。Agent 通过出站请求定时同步凭据，并使用本机 Unix Socket 向应用提供健康检查、取密和确认接口。

## 选择接入方式

| 方式 | 适用场景 | 应用需要完成的工作 |
| --- | --- | --- |
| Python SDK | 应用可以修改 Python 代码并直接访问 JumpServer | 定时取密、切换连接、确认版本和发送心跳 |
| Linux Agent | 不希望应用保存 JumpServer 密钥，或需要文件、EnvironmentFile、Unix Socket 交付 | 加载并验证 Agent 交付的凭据，再确认实际使用的版本 |

<!-- agent-doc:start -->

## Linux Agent 完整接入

下面以“单账号轮换 + JSON 文件交付”为例。从准备数据开始，完成 Agent 安装、首次取密和一次完整的凭据轮换。

### 接入前准备

确认以下条件已经满足：

- Agent 主机使用 systemd，已安装 Python 3.9 或更高版本，并能访问 JumpServer Core 地址。
- 你可以在 Agent 主机使用 `sudo`，而且应用运行用户已经存在。
- 目标资产和账号可以从 JumpServer 正常连接。
- 应用与 Agent 位于同一主机；容器化应用需要共享 Agent 的 Unix Socket 目录，并使用匹配的应用用户 UID。

### 创建应用凭据

1. 进入“应用管理 > 应用凭据”，创建一个应用凭据。
2. 凭据类型选择“账号轮换”，轮换方式选择“单账号轮换”。
3. 选择需要交付给应用的资产和账号，然后保存。
4. 记下凭据详情中的“接入标识”，后续命令使用的是这个值，而不是凭据名称。

### 授权应用账号

1. 进入“应用管理”，创建或打开目标应用。
2. 在应用详情的“账号”页面授权应用凭据使用的资产账号。
3. 如果使用双账号轮换，主账号和备用账号都必须授权。

在“客户端接入”中选择凭据不会自动增加账号授权。授权不完整时，Agent 无法获取凭据。

### 创建 Agent 接入配置

1. 打开应用详情的“客户端接入”，点击“创建”。
2. 客户端方式选择“Agent 接入”，并选择刚创建的应用凭据。
3. 填写应用运行用户和安装路径。默认安装路径为 `/opt/jumpserver-pam`。
4. 选择凭据交付方式并保存。

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

`<configuration-id>` 可以在接入配置详情中查看。安装路径、应用用户、Socket 路径以及可操作的 systemd 服务会在安装时固定；扩大这些权限需要重新安装 Agent。

### 安装 Agent

1. 打开 Agent 接入配置详情，点击“生成安装命令”。
2. 在 10 分钟内，将完整命令复制到应用主机执行。注册码只能使用一次。
3. 安装命令会创建 Python 虚拟环境、从 PyPI 安装 `jms-pam`、注册 Agent，并启动独立的 systemd 服务。

不要手工拼接或长期保存安装命令，因为其中包含一次性注册材料。

安装后检查服务：

```bash
sudo systemctl status jms-pam-agent-<configuration-id>.service --no-pager
```

使用接入配置中的应用运行用户检查本机接口：

```bash
sudo -u <app-user> curl --fail --silent --show-error \
  --unix-socket /run/jumpserver-pam/<configuration-id>/agent.sock \
  http://localhost/v1/health
```

正常响应示例：

```json
{"status":"ok","sync_status":"success"}
```

回到 JumpServer 的接入配置详情，确认实例显示“Agent 在线”且配置状态为“已同步”。Agent 默认每 30 秒同步一次，首次启动会立即同步。

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

生产应用应在真实连接验证和切换成功后自动调用本机确认接口；上述命令主要用于调试和人工兜底。Agent 会先在本机持久化确认状态，随后通过心跳自动补报 Core，因此 Core 暂时不可达不会要求应用再次确认。

成功响应包含 `key`、`revision`、`account_id` 和 `status: accepted`。确认接口是幂等的。不要因为文件写入、服务重启或 Webhook 送达就自动确认。

## 完整示例：完成一次凭据轮换

下面继续使用已经接入的单账号轮换凭据。

1. 进入“应用管理 > 应用凭据”，打开目标凭据并点击“开始轮换”。
2. 按页面提示创建账号改密任务。保存后进入任务列表，执行该任务。
3. 等待改密任务结束，回到应用凭据详情，点击“检查改密结果”。
4. 改密成功后，JumpServer 发布新的凭据 revision。Agent 会在下一次同步时获取新版本并按配置交付。
5. 应用加载新凭据、验证真实连接并切换成功后，使用文件或本机接口返回的实际 `revision` 执行确认命令。
6. 在凭据详情的“等待应用切换”区域确认所有 Agent 实例都已上报。
7. 点击“继续轮换”。状态变为“轮换完成”后，本次流程结束。

不要复制文档示例中的 revision。必须确认应用实际加载的 revision；确认旧版本会被 Agent 拒绝。

如果改密在真正修改密码前失败，修复网络、端口或执行环境后点击“重试”。如果状态为“密码需要核验”，先在“改密结果”中测试候选密码，再根据结果继续处理。

### 双账号轮换的差异

双账号轮换会执行两次应用切换：

1. JumpServer 先发布备用账号，等待每个实例加载、验证并确认备用账号。
2. 所有实例确认后，才允许修改主账号密码。
3. 改密成功后重新发布主账号，再等待所有实例确认。
4. 所有实例切回主账号后完成轮换。

任一启用实例离线或未确认当前 revision，都会阻止进入下一步。确认每个应用实例都有稳定且唯一的实例标识。

## Agent 本机接口

Agent 只在受保护的 Unix Socket 上提供本机接口，不监听 TCP 端口。Socket 默认属于接入配置中的应用运行用户，权限为 `0600`。

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

生产应用应在新凭据通过真实连接验证并完成切换后调用本机接口。随 Agent 安装的命令用于调试和人工兜底，应用不需要保存 Agent 密钥：

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

本机接口成功即表示确认状态已安全落盘；Agent 会在后续心跳中持续上报，直到 Core 接收。Core 短暂不可达不影响应用完成本机确认。

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

网络暂时不可达时，Agent 会继续保留最后一次有效缓存并重试。接入配置被禁用、授权被撤销或 Core 返回升级要求时，Agent 会停止通过 Socket 返回密码，但不会自动删除已经写入的文件。

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Python SDK 完整接入

下面以单账号轮换凭据为例，完成 SDK 配置、首次取密、应用确认和一次完整轮换。

### 接入前准备

1. 在“应用管理 > 应用凭据”创建“单账号轮换”凭据，并记录凭据接入标识。
2. 创建或打开目标应用，在“账号”页面授权该凭据使用的资产账号。
3. 在应用详情的“客户端接入”中创建 SDK 配置，并选择刚创建的应用凭据。
4. 打开 SDK 配置详情，点击“生成”，下载 `jms_pam_config.py` 并妥善保管。

每个应用进程或连接池都必须使用稳定且唯一的 `instance_id`。重新部署同一实例时应复用原标识，不同实例不能共享标识。

### 安装与配置

SDK 需要 Python 3.9 及以上。使用应用实际运行的 Python 或虚拟环境从 PyPI 安装：

```bash
python3 -m pip install --upgrade jms-pam
```

将 `jms_pam_config.py` 放入应用可以导入的位置。该文件包含应用身份信息，不要提交到代码仓库或输出到日志。

### 完整示例

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

    state = models.CredentialState(
        Key=response.Key,
        Revision=response.Revision,
        AccountId=response.Account.Id,
    )
    client.Heartbeat(models.HeartbeatRequest(Credentials=[state]))
```

应用应在自己的调度器中定时执行取密和心跳。只有新连接验证并切换成功后才能调用 `ConfirmCredential`；获取成功不等于应用已经使用该版本。

### 完成一次凭据轮换

1. 在“应用管理 > 应用凭据”中打开目标凭据并点击“开始轮换”。
2. 创建并执行账号改密任务，任务结束后点击“检查改密结果”。
3. JumpServer 发布新 revision 后，应用在下一次定时任务中调用 `GetCredential`；收到 Webhook 时也可以立即调用一次。
4. 应用使用新密码建立并验证连接，切换成功后调用 `ConfirmCredential`。
5. 在凭据详情确认所有 SDK 实例都已上报，然后点击“继续轮换”完成流程。

### SDK 常用方法

同步客户端提供以下常用方法：

- `GetCredential`：获取当前发布的凭据及 revision。
- `ConfirmCredential`：确认应用已经验证并使用指定 revision。
- `Heartbeat`：报告实例在线状态以及已经确认使用的凭据版本。

SDK 不启动后台线程，应用需要主动定时取密和发送心跳。应用收到 Webhook 后可以立即执行一次 `GetCredential`，但仍应保留定时轮询作为补偿。

HTTP、鉴权、网络和响应解析错误统一抛出 `jms_pam.common.exception.JumpServerPAMSDKException`。业务重试边界可以读取 `code`、`status_code`、`detail` 和 `original_error`。日志中不要记录凭据或认证请求头。

<!-- sdk-doc:end -->
