# Go jms-pam-agent

Agent 是独立 Go 二进制，运行时不依赖 Python。内置 systemd 安装仅支持 Linux/root；Linux、macOS 和 Windows 可由当前用户前台运行。Linux 服务使用本机私有配置 `/etc/jms-pam-agent/agent.json`。

```bash
systemctl start jms-pam-agent
systemctl status jms-pam-agent
systemctl restart jms-pam-agent
journalctl -u jms-pam-agent
```

服务固定为 `jms-pam-agent.service`。身份使用应用 AK/SK 和稳定的 `instance_id`。应用授权账号决定按需 pull 范围；应用绑定的凭据策略决定主动同步和推送范围。每个业务副本使用稳定、唯一的 `instance_id`。

新建应用或修改账号授权时，可以选择具体账号、全部账号或按属性选择账号。匹配的账号数受系统全局上限约束，默认 10 个；在 Core 的 `config.yml` 中通过 `APPLICATION_ACCOUNT_SCOPE_LIMIT` 调整，修改后需重启 Core。已有授权在修改账号范围前保留原有取密能力。新授权的动态范围日后超过上限时，账号列表与取密请求会失败，直到缩小范围或调高上限；服务端不会任意截取前 10 个账号。保存新范围后，Agent 按下一次同步结果撤销不再授权的账号 push key。

## 安装

在仓库的 `apps/accounts/clients/go` 或下载的 Go SDK 源码目录构建。构建需要 Go 1.23+；目标 Linux 主机只需要二进制和 systemd。

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
# ARM64 主机使用 GOARCH=arm64。
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id orders-node-1
sudo systemctl start jms-pam-agent
```

引导文件从应用接入向导下载，包含 AK/SK。安装时通过签名同步获取并固定交付能力，配置写入 `/etc/jms-pam-agent/agent.json`，最新凭据和运行状态写入 `/var/lib/jms-pam-agent/state.json`，均为 `0600`。安装启用并启动固定服务；重复安装核对身份，不更换已有身份。构建产物需要匹配目标架构。

## 运行流程

`更新通知 / 首次及重连快照 → 签名核对授权与版本 → 实时取密 → 保存最新凭据 → 渲染 → 备份现有业务配置 → 原子替换文件 → 执行动作 → 保存交付版本`

- 默认按 key 写 JSON 文件，也支持 EnvironmentFile 和 Unix Socket。默认目录及 socket 路径由本机文件指定，具体值在本机 `delivery` 中。
- 本机 `rules` 可以指定其他服务的配置路径、可信模板，以及 reload/restart 或固定脚本。
- 更新业务配置前，Agent 将现有目标文件备份到 `state_file` 所在目录的 `backups/`，按目标路径分别存放，文件名带 UTC 日期时间；每个目标最多保留最近 10 份。备份目录仅 Agent 可访问，备份文件为 `0600`。相同内容不会重复备份。备份失败会阻止本次更新；新建文件没有旧内容可备份。超过 32 MiB 的目标文件需要由业务自行管理备份。
- 同一版本成功交付后跳过重复动作；初次交付、新版本和失败重试执行动作。通知仍会主动取密。
- 获取或交付失败按 1–30 秒指数退避重试，并每 300 秒对账。读取器使用有界队列，业务动作串行执行；WebSocket 心跳与重连由 Go SDK 管理。
- 最新成功获取的密码不按时间过期，刷新失败不丢失，Agent 重启可恢复。更旧的 API 响应不会覆盖新版本。
- 明确撤销或授权快照缩小会先停用相应本地取密并保存范围，再尝试 HTTP 同步；HTTP 身份拒绝阻断本地访问。已写入业务文件不会因网络错误被删除。
- `received`、保存最新值、文件交付和业务生效分别记录。文件写入、脚本退出或服务重启本身不会确认轮换；只有本机 `application_check` 显式配置 `confirm_on_success` 且成功验证运行中的应用，Agent 才确认准确版本。

## 本机配置

从应用接入向导下载配置，安装时指定稳定的实例 ID。通常只需编辑 `rules`：一个规则声明业务实际使用的账号，以及如何更新配置、让服务重新读取配置、验证运行中的连接。Core 不能通过事件修改本机脚本和目标路径。

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "app_user": "orders"
  },
  "rules": [
    {
      "accounts": [
        {
          "account_id": "<主库账号 A ID>",
          "allow_account_switch": true
        }
      ],
      "config_update": {
        "file": "/opt/jumpserver/config/config.txt",
        "fields_map": {"DB_USER": "username", "DB_PASSWORD": "secret"}
      },
      "service_action": {"path": "/usr/local/libexec/jms-pam/recreate-jumpserver"},
      "application_check": {
        "path": "/usr/local/libexec/jms-pam/check-running-db",
        "confirm_on_success": true
      }
    }
  ]
}
```

`account_id` 是 JumpServer 账号 ID，不是数据库用户名或凭据策略 ID。使用 `config_update.file` 时，一条规则只声明一个账号；`fields_map` 直接指定文件字段如何取值：上例把当前生效账号的 `username`、`secret` 写入 `DB_USER`、`DB_PASSWORD`。`allow_account_switch` 允许该账号参与 A/B 轮换：事件声明 A、B 后，Agent 在 A→B、B→A，以及首次同步已选中 B 时，均使用 A 的规则，把当前账号的值写到同一组字段。普通账号省略 `allow_account_switch`。

调试文件若有 `VERSION` 字段，可在 `fields_map` 中增加 `"VERSION":"revision"`，随凭据版本自动更新。这里的 `revision` 是凭据策略的交付版本，不是账号密码历史版本；正式业务文件没有该字段时不需要添加。

规则按以下顺序执行。只有业务实际使用新连接后，`application_check` 才应成功；`confirm_on_success` 才会确认准确的轮换版本。失败会保留待交付状态并重试。

| 配置块 | 作用 |
| --- | --- |
| `credential_check`（可选） | 在改业务配置前，尝试用新账号连接目标数据库。 |
| `config_update` | 按 `fields_map` 定点修改现有文件；复杂格式可改用模板或脚本。 |
| `service_action` | 执行固定脚本，或对固定 systemd unit 执行 reload/restart。 |
| `application_check` | 验证运行中的业务已经通过新账号完成真实数据库操作。 |

上例适用于安装器的 `config.txt`：Agent 只改现有的 `DB_USER`、`DB_PASSWORD`，保留其他设置和文件权限；生效脚本重建读取环境变量的 Core、Celery 容器。直接部署的扁平 `config.yml` 只需把 `file` 改成该 YAML 文件，随后重启实际读取它的进程。Agent 根据 `.txt` / `.yml` 扩展名识别格式，也可显式指定 `format: "env"` 或 `format: "yaml"`。映射的字段必须已存在且不能重复；复杂或嵌套格式使用脚本。安装器 `config.txt` 的密码不能含引号，遇到此类值 Agent 会失败而不会写入可能无法读取的配置。两种部署都要验证真实数据库连接，进程存活不足以确认切换。

如果业务使用两个账号，分别写两条规则，各自声明一个账号和对应的 `fields_map`。两条规则可以指向同一文件，但字段不能重叠，文件格式和 `owner` 也必须相同。例如第二条规则使用 `{"accounts":[{"account_id":"<报表库账号 ID>"}],"config_update":{"file":"/opt/jumpserver/config/config.txt","fields_map":{"REPORT_DB_USER":"username","REPORT_DB_PASSWORD":"secret"}}}`。同一次交付涉及两条规则时，Agent 依次基于文件最新内容更新各自字段，全部文件更新后再执行服务动作和业务验证。

特殊格式可将 `config_update` 改为 `{"target":"/path/config","script":{"path":"/usr/local/libexec/jms-pam/update-config"}}`。脚本修改多个文件时使用 `targets` 列出全部目标。声明目标用于路径安全与冲突检查，Agent 不会把路径自动作为脚本参数传入。

更新、重启和检查脚本都从标准输入读取 JSON，例如：

```json
{
  "event": "credentials.updated",
  "credentials": {
    "<主库账号 A ID>": {
      "account_id": "<当前账号 B ID>",
      "username": "db_user_b",
      "secret": "<latest-password>"
    }
  }
}
```

脚本必须按声明的账号 ID 读取 `credentials`，不能依赖数组位置。它没有隐式参数；需要固定参数时在 `args` 中声明。密码不放在参数、环境变量或日志中。脚本须支持重复执行，失败时以非零状态退出。Agent 会在调用更新脚本前备份其声明的 `target` / `targets`；脚本修改声明范围外的文件由脚本自行负责。写入业务文件后若启动或检查失败，Agent 会重试，但不会自动回滚该文件；恢复备份后仍需让业务重新读取配置，并验证连接。默认超时 120 秒，可用 `timeout_seconds` 调整，最大 300 秒。脚本路径及其父目录必须可信，目标目录也须受保护且不能使用符号链接。

如果业务文件由 Agent 完整生成，`config_update` 可改为模板：

```json
{
  "files": [
    {"path": "/etc/order-service/database.json", "template_file": "/etc/jms-pam-agent/orders-db.tmpl"}
  ]
}
```

模板中的账号索引为本机声明的 ID，例如 `{{json (index .Credentials "<主库账号 A ID>").Secret}}`。模板会替换整个文件；需要保留其他配置项时优先使用上述字段映射，复杂格式再使用更新脚本。`service_action` 也可写成 `{"unit":"order-service.service"}`，默认 restart；需要 reload 时显式设置 `operation: "reload"`。只读取启动环境的服务应选择 restart。

`state_file`、`event_file`、`reconcile_interval`、`delivery.socket_path` 均有内置默认值，只有需要调整时才填写。`rules` 为空时，Agent 默认按凭据 key 在 `delivery_root` 写 JSON 文件；此模式不负责修改业务配置。修改配置后检查并重启 Agent：

```bash
sudo chmod 0600 /etc/jms-pam-agent/agent.json
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```

轮换流程中，先验证备用账号，再下发切换并等待各 Agent 的业务验证；之后根据 JumpServer 取密记录判断旧账号已无流量，才允许修改旧账号密码。`application_check` 只证明对应应用副本已切到新连接，不能代替旧账号无流量的门槛。

## 本地 API 与生效确认

Socket 归 `app_user` 所有，权限 `0600`，父目录为 root 管理的 `0750`。按本机 `delivery.socket_path` 请求：

```bash
curl --unix-socket '<socket-path>' http://localhost/v1/health
curl --unix-socket '<socket-path>' http://localhost/v1/credentials/orders-db
jms-pam-agent confirm orders-db --revision 3 --socket '<socket-path>'
```

应用验证真实连接并成功切换后，才确认准确版本：业务可通过本机接口显式确认，也可使用通过检查脚本验证的 `confirm_on_success`。同步运行的检查脚本不应反向调用 Agent 的确认接口。交替轮换需要确认，凭据订阅无需确认。确认先持久化，Core 不可用时返回 `pending` 并重试；Core 接受后为 `confirmed`。手动切换指令只在相应版本已确认生效后报告成功。重启指令只操作本机已经固定为 restart 的 systemd 服务。

旧 Python Agent 和旧配置格式已移除。修改旧安装时先停止旧进程，按新格式重新生成配置并完成在线同步，再接管交付位置；旧状态不自动转换。

## CLI 查询账号和凭据

CLI 通过正在运行的 Agent 的私有 Unix Socket 查询，复用它的身份、授权和持久化状态：

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
# 自定义配置或直接指定应用用户可访问的 Socket：
jms-pam-agent get_accounts --config /path/to/agent.json
jms-pam-agent get_secret '<account-id>' --socket '<socket-path>'
```

也支持 `get-accounts` / `get-secret`；旧命令 `get_credential` / `get-credential` 仍可用。`get_accounts` 不取密码，列出应用授权 pull 的账号和资产；未订阅 push 的账号也会列出，其 `credentials` 为空。策略只显示主动同步范围，轮换策略只标注当前生效账号。`get_secret ACCOUNT_ID` 直接在线核对应用授权并按需取密，不要求账号绑定凭据策略，也不会把仅 pull 的密码写入 Agent 的持久化状态。账号列表 API 支持 `limit`、`offset` 和 `search`。

`--config` 可以使用相对当前工作目录的路径，例如 `--config subscription/agent.json`。加载后仍检查私有权限和符号链接；配置内容中的状态、Socket、交付文件等路径必须为绝对路径。CLI 失败时显示具体的本机检查原因或 HTTP 状态，不输出后端错误正文。

输出为 JSON，`source` 为 `api` 或 `local`。只有网络错误、超时或 HTTP 5xx 才允许返回仍授权的 push 凭据缓存；仅 pull 的凭据在离线时不可用。授权拒绝、撤销、错误响应和版本回退都返回失败。离线账号列表仅包含已经保留凭据且仍授权的账号。取密命令会将密码输出到 stdout，Agent 自身日志和事件文件不会记录密码。查询不会上报业务生效确认。

## Linux / macOS / Windows 前台运行

本地开发无需 root 或 systemd。先从现有应用的 Agent 接入向导下载引导 JSON，设置 `0600`，选择 JSON 或 Socket 交付。在 Go SDK 目录执行：

```bash
go build -o jms-pam-agent ./cmd/jms-pam-agent
chmod 600 /private/path/jms_pam_agent.json
./jms-pam-agent init-local \
  --bootstrap /private/path/jms_pam_agent.json \
  --directory "$HOME/.jms-pam-agent/orders" \
  --instance-id local-orders-agent
./jms-pam-agent run --local --config "$HOME/.jms-pam-agent/orders/agent.json"
```

Windows 从 Go SDK 目录构建 `GOOS=windows GOARCH=amd64 go build -o jms-pam-agent.exe ./cmd/jms-pam-agent`，然后在引导文件所在目录用 PowerShell 运行：

```powershell
$agentDir = Join-Path $HOME 'jms-pam\orders'
.\jms-pam-agent.exe init-local --bootstrap (Join-Path $PWD 'jms_pam_agent.json') --directory $agentDir --instance-id $env:COMPUTERNAME
.\jms-pam-agent.exe run --local --config (Join-Path $agentDir 'agent.json')
```

Windows 需要支持 AF_UNIX 流套接字。

`init-local` 通过签名同步确认现有应用范围，生成当前用户的本机路径；只需初始化一次，后续启动复用 `agent.json`。Windows 的引导文件与凭据路径须位于当前用户主目录下，并具有私有 ACL；Agent 拒绝链接和重解析点。本地 Socket 路径需短于 108 字节。Windows 默认凭据文件名使用 key 的 SHA-256 哈希，JSON 内容仍保留原 key。前台模式使用应用授权范围和本机交付规则，支持 JSON 或 Socket，拒绝 EnvironmentFile 与 systemd 动作；Windows 可信脚本动作仅接受 `.exe`。模板、脚本和显式文件规则需自行指定受保护的本机路径。Linux 生产服务仍使用固定 `systemctl start jms-pam-agent`。

目录中：

- `agent.json`：身份及本机规则。
- `events.jsonl`：追加事件元数据，包括 `received`、`saved`、`delivered` 阶段和 UTC 时间；不含密码。
- `credentials/<key>.json`：默认 JSON 模式原子替换的最新密码及账号、版本信息。
- `state.json`：最新成功取密值、授权、交付和确认状态，支持离线重启。
- `run/agent.sock`：CLI 和应用的本地访问入口。

以上配置、事件和凭据文件均为 `0600`。生产配置也可以设置可选的绝对路径 `event_file`，该路径必须与状态和凭据交付文件分开。事件日志是本机观察记录，不提供后端历史事件重放或恰好一次保证。写文件不代表真实服务已切换连接；这个简单示例不会自动确认轮换。

在另一个终端查询：

```bash
./jms-pam-agent get_accounts --config "$HOME/.jms-pam-agent/orders/agent.json"
./jms-pam-agent get_secret '<account-id>' --config "$HOME/.jms-pam-agent/orders/agent.json"
```

## 本地验证

```bash
go test -race ./agent
go build ./cmd/jms-pam-agent
```

单测验证文件渲染、原子替换、脚本标准输入和超时、更新取密、离线重启、撤销、失败重试、生效确认与 Socket 生命周期。Linux systemd 安装和真实业务 reload/restart 应在目标主机验证。
