# JumpServer PAM Python SDK 与 Agent

## Python SDK

环境要求：Python 3.9 及以上。

### URL 安装

在应用详情的「客户端接入」中生成配置，复制安装命令执行。以下为本机 JumpServer 地址示例：

```bash
python3 -m pip install --index-url https://pypi.org/simple http://127.0.0.1:8080/api/v1/accounts/python-sdk/
```

SDK 源码从 JumpServer 下载；setuptools 等构建工具以及 requests 等运行依赖从官方 PyPI 下载。安装时需能访问 JumpServer 和软件源，不需要本地 `packages` 目录。请使用应用实际运行的 Python 或虚拟环境；在其他机器安装时，用页面生成的、该主机可访问的 JumpServer 地址，不能沿用 127.0.0.1。

如果出现 `installing build dependencies` 和 `No matching distribution found for setuptools`，使用 `pip -v` 查看软件源访问错误。清华镜像返回 403 时不代表 setuptools 版本不存在；上述命令显式指定官方源，仅影响本次安装，不改全局 pip 配置。企业限制公网时请将 `--index-url` 替换为可用且提供这些依赖的内部源，不要用 `--no-deps` 或 `--no-build-isolation` 掩盖缺失依赖。

### 应用接入

在应用详情的「客户端接入」中创建配置、选择应用凭据，再下载 `jms-pam.json`。文件已包含地址、应用 ID、密钥、组织 ID 和接入配置 ID，不需要另找参数。请按敏感文件保管。

```python
from jms_pam import JumpServerPAMClient

client = JumpServerPAMClient.from_config('jms-pam.json')

credential = client.get_credential('cred-pg-main')

new_pool = create_pool(
    username=credential.username,
    password=credential.secret,
)
new_pool.check_connection()
old_pool.close()

client.confirm_applied(credential)
```

应用运行期间需要定期调用 `get_credential()` 获取最新版本。取到凭据不代表应用已经使用它；成功建立新连接并释放旧连接后，才调用 `confirm_applied()`。SDK 自动每 30 秒上报心跳。

同一个应用有多个运行副本时，建议给每个副本设置稳定的实例标识：

```bash
export JMS_PAM_INSTANCE_ID=order-service-node-1
```

## Linux Agent

Agent 支持 Python 3、Linux 和 systemd。应用从 `/etc/jumpserver-pam/credentials.json` 读取当前账号，Agent 本地接口只监听 `127.0.0.1:8081`，不提供取密接口，也不使用本地认证。

页面生成的 Agent 命令会创建虚拟环境，从 JumpServer URL 安装 SDK/Agent，并连接 JumpServer 注册；构建和运行依赖使用命令中指定的软件源。注册材料有效期为 10 分钟且只能使用一次。已安装 Agent 时，注册命令如下（请使用安装所在虚拟环境的 `jms-pam-agent`）：

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
