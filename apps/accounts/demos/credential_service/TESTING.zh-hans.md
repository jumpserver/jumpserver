# 凭据策略完整测试步骤

本文覆盖管理页面、固定账号轮换、临时账号签发、应用签名、租约、停用回收、故障恢复和 Vault 清理。测试账号必须可丢弃；禁止直接对生产账号做首次验证。

## 1. 支持范围

- 固定账号轮换：由资产平台的 `change_secret_enabled + change_secret_method` 能力决定。
- 临时账号：首版实际支持 POSIX、Windows 本地账号、Windows AD、MySQL、PostgreSQL、MongoDB、Oracle、SQL Server 的创建和删除适配器。
- AWS IAM、网络设备、云服务和 Web/自定义应用尚未实现临时账号创建/删除，不应创建动态策略。
- 管理页面不签发或显示密码；临时凭据只能由绑定应用通过 HMAC 接口申请。

## 2. 环境准备

1. 执行数据库迁移，启动 Core、Celery default worker 和 ansible worker。
2. 准备一个 Integration Application，保存应用 ID、Secret、组织 ID，并把测试机 IP 加入允许范围。
3. 准备一个支持改密的测试资产、一个允许 `secret_reset` 的普通账号，以及一个有可用密码的特权管理账号。
4. 动态测试再准备一个启用自动推送的账号模板；模板密码策略和结构化推送参数应与资产平台匹配。
5. 客户端和 JumpServer 使用 NTP 校时；接口测试只通过 HTTPS。

本地开发环境若没有 `jumpserver/ansible-executor:latest` 镜像，可仅对本次测试进程关闭 Ansible Docker 隔离。必须先激活虚拟环境，确保 worker 的子进程能找到 `ansible-playbook`：

```zsh
cd /Users/nut/develop/jumpserver
source .venv/bin/activate
export ANSIBLE_DOCKER_ENABLED=false
export ANSIBLE_LOCAL_TEMP="$(mktemp -d /private/tmp/jms-ansible-local.XXXXXX)"
export ANSIBLE_REMOTE_TEMP=/tmp/.ansible-jms
SERVER_SIZE=large python apps/manage.py start task
```

该方式只用于本地测试，不修改持久配置。生产环境应准备项目要求的执行器镜像并保持 Docker 隔离。修改凭据任务代码后必须重启 `celery_ansible`，并确认没有加载旧代码的同名 worker 仍在消费 `ansible` 队列。

管理页面入口：

```text
/ui/#/pam/integrations/services/{application_id}?tab=CredentialPolicies
```

## 3. 自动检查

### 3.1 后端

```bash
cd /Users/nut/develop/jumpserver

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python apps/manage.py check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  apps/manage.py makemigrations accounts --check --dry-run
git diff --check
```

运行不依赖测试数据库的凭据逻辑测试：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import os
import sys
import unittest

sys.path.insert(0, 'apps')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')

import django
django.setup()

suite = unittest.defaultTestLoader.loadTestsFromName('accounts.tests')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

标准 CI 或具备独立测试数据库配置的环境还应运行：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  apps/manage.py test accounts.tests --keepdb -v 2
```

本机若在创建测试数据库前出现现有配置错误 `KeyError: 'TEST'`，不能把它记为功能测试通过；应在 CI 的标准数据库配置中补跑。

验证八个临时账号 Playbook 的语法：

```bash
for playbook in \
  apps/accounts/automations/push_account/host/posix/main.yml \
  apps/accounts/automations/push_account/host/windows/main.yml \
  apps/accounts/automations/push_account/host/windows_ad/main.yml \
  apps/accounts/automations/push_account/database/mysql/main.yml \
  apps/accounts/automations/push_account/database/postgresql/main.yml \
  apps/accounts/automations/push_account/database/mongodb/main.yml \
  apps/accounts/automations/push_account/database/oracle/main.yml \
  apps/accounts/automations/push_account/database/sqlserver/main.yml
do
  ANSIBLE_LIBRARY=/Users/nut/develop/jumpserver/apps/libs/ansible/modules \
  ANSIBLE_LOCAL_TEMP=/private/tmp/jms-ansible-local \
  ANSIBLE_REMOTE_TEMP=/tmp/.ansible-jms \
  .venv/bin/ansible-playbook --syntax-check "$playbook" || exit 1
done
```

### 3.2 签名客户端

```bash
cd /Users/nut/develop/jumpserver
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  apps/accounts/demos/credential_service/client.py self-test
```

固定向量必须同时验证 JSON 字节、Digest 和最终 HMAC 签名。

### 3.3 Lina

Lina 要求 Node `>=24 <25` 和 Yarn 4：

```bash
cd /Users/nut/develop/lina
export PATH=/Users/nut/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin

node --version
corepack yarn --version
corepack yarn lint
corepack yarn fmt:check
corepack yarn build
git diff --check
```

## 4. 固定账号轮换

1. 进入应用详情的“凭据策略”，创建“固定账号轮换”策略。
2. 依次选择资产、目标账号；管理账号留空时应自动绑定该资产最近更新的特权账号，也可显式选择。
3. 保存后确认：
   - 策略状态为 `enabled`；
   - `current_version=1`；
   - 版本历史存在版本 1；
   - 目标端密码没有在创建策略时被修改。
4. 应用读取版本 1 并验证能登录目标资产。
5. 在页面点击“立即轮换”，确认接口返回 `202`，状态先变为 `rotating`。
6. 等待 ansible 任务结束，确认状态恢复 `enabled`、版本变为 2、新密码可登录、旧密码不可登录。
7. 再次读取，确认只返回版本 2；版本记录只保存账号版本和执行引用，不保存历史密码。
8. 断开资产网络后再轮换：
   - 明确失败时保留旧可用版本；
   - 无法确认远端结果时策略进入 `uncertain`；
   - `rotating`/`uncertain` 状态下应用读取返回 `503`，不返回密码。
9. 恢复网络并手工轮换成功后，才能恢复应用读取。

## 5. 应用读取固定凭据

```bash
export JMS_URL='https://jumpserver.example.com'
export JMS_APP_ID='应用 ID'
export JMS_APP_SECRET='应用 Secret'
export JMS_ORG_ID='组织 ID'
export JMS_TIMEOUT='35'

python3 apps/accounts/demos/credential_service/client.py fixed "$STATIC_POLICY_ID"
python3 apps/accounts/demos/credential_service/client.py fixed \
  "$STATIC_POLICY_ID" --etag '"上次响应中的 ETag"'
```

验收：第一次为 `200`，响应含 `Cache-Control: no-store`、用户名、密码、版本和 ETag；第二次为 `304` 且不含密码。应用 B 读取应用 A 的策略必须返回 `404`。

## 6. 临时凭据完整闭环

1. 创建“临时账号”策略，选择支持动态账号的资产、账号模板和管理账号。
2. 配置用户名模板、默认 TTL、最大 TTL、最大活跃租约数和平台结构化参数。
3. 申请凭据：

```bash
export REQUEST_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

python3 apps/accounts/demos/credential_service/client.py issue \
  "$DYNAMIC_POLICY_ID" --idempotency-key "$REQUEST_ID"
```

4. 验收签发结果：
   - 请求在 30 秒内直接返回 `username`、`secret`、`lease_id`、TTL 和到期时间；
   - 目标端账号存在并可用返回的密码真实登录；
   - JumpServer 账号列表中存在 `source=credential_lease` 的 `Account`；
   - 管理页面“临时凭据”出现 active 租约；
   - 签发完成后请求记录不再保留临时密码。
   - 数据库中 `CredentialIssueRequest.provisional_secret` 为 `NULL`，不是加密后的空字符串。
5. 用同一个 `Idempotency-Key` 再请求一次。客户端会生成新 Nonce；应返回同一个请求、账号和租约，不能创建第二个目标账号。
6. 查询和续租：

```bash
python3 apps/accounts/demos/credential_service/client.py lease "$LEASE_ID"
python3 apps/accounts/demos/credential_service/client.py renew \
  "$LEASE_ID" --increment 120
```

7. 确认查询永远不返回密码，续租只延长 `date_expires`，不修改账号密码，且不超过 `date_max_expires`。
8. 应用主动撤销：

```bash
python3 apps/accounts/demos/credential_service/client.py revoke "$LEASE_ID"
```

9. 管理员也可在页面续租或回收。首次回收通常返回 `202 revoking`；最终应满足：
   - 目标端账号不存在；
   - JumpServer `Account` 已删除；
   - Vault 当前值和历史值已删除；
   - Lease 仍保留用户名、状态、时间、执行引用和错误审计，但没有密码。

## 7. 各动态平台的实测项

每个对外声明支持的适配器都执行第 6 节，并额外验证：

- POSIX：主组、附加组、shell、home、sudo。
- Windows / Windows AD：用户组。
- MySQL：账号 host 或 all-hosts 行为。
- MongoDB：roles。
- PostgreSQL、Oracle、SQL Server：默认数据库、角色及平台已有结构化参数。
- 预先创建同名账号后再签发，应返回 `ACCOUNT_ALREADY_EXISTS`，不得接管已有账号。
- SSH key 模板当前只对 POSIX 动态账号使用；不兼容平台必须在创建策略时被后端拒绝。

发布门槛至少真实通过 POSIX 和一个数据库闭环；其余标为支持的适配器应逐一完成同样验证。

## 8. 停用与队列优先级

### 8.1 动态策略

1. 先创建两个 active 租约，再启动一个故意延迟的签发。
2. 点击停用，状态应立即变为 `disabling`。
3. 新签发和续租立即返回 `403`，所有已有租约进入 `revoking`。
4. 回收使用现有 ansible 队列的 priority 0；不会抢占正在执行的任务，但应排在已等待的 priority 5/9 任务之前。
5. 所有签发请求、租约和本地账号清理完成后，策略才变为 `disabled`。
6. 远端删除失败时仍删除本地 `Account`，租约记录 `revoke_succeeded=false` 和错误原因。

### 8.2 固定策略

- 轮换仍为 pending：停用应取消该执行并立即变为 `disabled`。
- 轮换已经 running：状态先变为 `disabling`，应用读取立即返回 `403`，待运行结果收敛后再变为 `disabled`。
- 重新启用前，处于不确定状态的账号必须先成功轮换。

## 9. 签名与权限负向测试

| 场景 | 期望 |
| --- | --- |
| 同一签名和 Nonce 重放 | `401` |
| Date 偏移超过正负 5 分钟 | `401` |
| 算法改为 `hmac-sha1` | `401` |
| 错误组织 ID、来源头或 Digest | `401` |
| `Idempotency-Key` 未加入签名头列表 | `401` |
| 调用 IP 不在应用白名单 | `401` |
| Integration Application 已停用 | `401` |
| 应用 B 访问应用 A 的策略或租约 | `404` |
| `SECURITY_DISABLE_VIEW_SECRET=true` | 固定读取和临时签发均为 `403` |
| 策略 disabled/disabling | 读取、签发、续租立即为 `403` |
| 管理员仅有 view 权限 | 页面可见，但创建、轮换、停用、续租、回收不可用 |

还应检查浏览器 Network、DOM、应用日志、APM、指标和异常栈，确认没有密码、应用 Secret 或完整 Authorization。

## 10. Worker 与故障恢复

1. 在轮换、签发或回收期间强制终止 ansible worker。
2. 等待执行 hard deadline、60 秒 grace 和下一次 reconciler。
3. 重启 worker。
4. 超时执行应变为 canceled；静态策略进入 `uncertain`，动态签发进入 cleanup/revoke。
5. cleanup/revoke 重复执行不能创建第二个账号、租约或执行记录。
6. 不允许残留可读取密码或永久 running 的执行。

## 11. Vault 清理

对实际启用的每种 Vault 后端至少签发并撤销一次：

| 后端 | 撤销后的验收 |
| --- | --- |
| Local | `Account` 与全部 `HistoricalAccount` 不存在 |
| OpenBao KV v2 | 对应 metadata 路径返回 404，全部版本被删除 |
| HCP Vault | metadata 和全部版本不存在 |
| AWS Secrets Manager | 最终返回 ResourceNotFound，不能只进入 recovery window |
| Azure Key Vault | 当前 secret 和 deleted secret 都不存在 |

Azure 开启 purge protection 时无法立即物理销毁；测试环境必须允许 purge。另测试 Vault 暂时不可达：回收失败应留下租约错误，恢复 Vault 后由 reconciler 重试，最终清理全部密码内容。

## 12. 页面验收

1. 从“应用管理”进入详情，不依赖原型参数即可看到“凭据策略”；刷新带 `?tab=CredentialPolicies` 的地址仍停留在该页签。
2. 验证策略、临时凭据、轮换版本、签发记录均只显示当前应用的数据，并支持搜索、分页、刷新、空状态和接口错误状态。
3. 创建表单是单个完整大表单；切换模式会清空不兼容的资产、账号、模板和平台参数。
4. 资产选择受平台能力预过滤；最终能力和模板兼容性以服务端校验为准，页面不得展示静态 mock 能力矩阵。
5. 静态流程可查看详情、立即轮换、停用、启用和版本历史。
6. 动态流程可查看全部租约、续租、回收及错误；管理页面没有“申请临时凭据”或“查看密码”按钮。
7. 详情中的应用接入区域显示正确应用 ID 和真实 GET/POST 路径，可复制但不读取应用 Secret。
8. “调用记录”继续展示应用请求审计；“历史记录”只展示轮换版本和签发记录，不伪造按策略的读取历史。
9. 分别切换简体中文、繁体中文、英文和日文，不能出现该页面新增的硬编码中文。
10. 测试 Root 组织、无权限、非活动应用、不支持资产、服务端 `400/403/503` 和超长错误文案。

## 13. 发布判定

必须同时满足：自动检查全绿；固定账号完成一次成功轮换和一次故障收敛；POSIX 与一个数据库完成动态签发、续租、回收；签名负向测试通过；策略停用能立即阻断新请求；浏览器、日志、Vault 和历史表均不存在历史密码内容。
