# 两个文件配置 Demo 应用

两个进程使用仓库现有的 Python SDK 接入凭据事件流：

- `file_apps.subscription`：订阅策略选定账号的密码变化，按账号 ID 更新本地 JSON。
- `file_apps.rotation`：接收账号轮换（当前支持双账号），更新本地 JSON，读回确认后调用 `ConfirmCredential`。

配置文件包含密码，写入时采用同目录临时文件和原子替换，文件权限为 `0600`。日志只显示账号或策略标识和版本。每个副本使用独立输出文件及唯一 `instance_id`；在 K8s 中可用 Pod 名称作为实例标识，并为每个 Pod 挂载自己的写入目录。

## 接入 JumpServer

需要提前准备一个用于订阅的资产账号，以及**同一资产**上的两个用于交替轮换的账号。对每个 Demo 分别执行：

1. 在“应用管理”创建一个应用，授权它需要读取的账号；轮换应用必须同时授权两个账号。
2. 在“凭据策略”创建相应模式的策略，绑定刚创建的应用；订阅策略还需选择要通知的账号。
3. 在策略的“接入配置”创建 **SDK 接入**，选择该策略。
4. 在接入配置详情点击“生成”，下载 `jms_pam_config.py` 到仓库外的私有目录。两份 Demo 必须各用自己的配置文件，不能共用应用密钥或接入配置。

这四步分别建立应用、账号授权、策略绑定和接入配置；只创建策略不足以让 Demo 取密。

## 启动

在 `apps/accounts/demos/python` 目录安装本地 SDK：

```bash
python3 -m pip install -e .
```

启动两个独立进程。下面路径只是示例，请替换为“生成”步骤实际下载的位置：

```bash
python3 -m file_apps.subscription \
  --config /private/jms-pam/subscription/jms_pam_config.py \
  --instance-id subscription-pod-1 \
  --output /private/jms-pam/subscription/application.json

python3 -m file_apps.rotation \
  --config /private/jms-pam/rotation/jms_pam_config.py \
  --instance-id rotation-pod-1 \
  --output /private/jms-pam/rotation/application.json \
  --confirm-file-only
```

启动后 WebSocket 的首次快照会拉取当前版本并生成本地文件。订阅应用在 `credential.updated` 时更新对应账号；轮换应用在收到 `credential.updated` 后写入并读回文件。示例命令使用 `--confirm-file-only`，读回成功后上报轮换确认；不加此参数则只更新文件，不上报确认。`configuration.updated` 会触发重连并用新快照对账；快照中消失的账号或策略会从本地文件移除。

轮换 Demo 的“生效”仅指这个示例的文件内容已更新。真实应用必须先使用新账号验证业务连接并切换连接池，再调用 `ConfirmCredential`。不要把文件写入确认当作数据库连接成功的证明。

测试：

```bash
python3 -m unittest discover -s file_apps/tests -v
```
