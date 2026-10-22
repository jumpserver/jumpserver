# SSH Ansible executor

Core 复用原 `ANSIBLE_DOCKER_ENABLED` 隔离开关：开启时使用常驻 SSH 执行器，
关闭时在当前 Core/Celery 进程所在环境执行。SSH 后端复用现有
AdHocRunner、PlaybookRunner、SuperPlaybookRunner、UploadFileRunner 和回调；
Celery 将任务目录传给常驻的 OpenSSH 执行容器，任务以独立 UID 运行。
Core/Celery 不需要 Docker socket，也不会调用本地 bwrap。SDK 源码和服务端在
[jumpserver/ansible-executor](https://github.com/jumpserver/ansible-executor)。

## 配置

先按[配套 executor 说明](https://github.com/jumpserver/ansible-executor/blob/fa6aca21ae501da85e559b2d0dc1e0955be441e3/README.md)
部署 `jumpserver/ansible-executor:<版本或分支>`，生成每套部署独立的服务密钥。
正式版标签与 Core 版本一致，不带 `-ce` / `-ee`；开发版使用对应分支标签。
`latest` 保留给旧版逐任务容器，不适用于 SSH 后端。
上述服务端提交补齐了业务依赖、账号自动化 SSH 包装脚本和网关私钥/密码文件的路径转换，
兼容 Core 当前锁定的 SDK。任务目录 `/home/jms-executor` 使用 tmpfs 时需要
`exec,nosuid,nodev`，否则随任务上传的脚本无法执行。
执行容器所在 Linux 内核及 seccomp 策略需要允许 `pidfd_open` 和
`pidfd_send_signal`；不支持时服务端会拒绝创建会话。sshd 需要容器内 root，
无需 privileged、SYS_ADMIN 或宿主机 PID namespace。
将公钥挂载给 executor，只将私钥及可信取得的服务器 host key 挂载给 Core/Celery。
私钥不要放进任务目录、Playbook 或环境变量。`known_hosts` 中必须使用实际连接
地址；非 22 端口的格式是 `[ansible-executor]:2222 ssh-ed25519 ...`。
资产地址也必须能从执行容器访问；`127.0.0.1` 指向执行容器本身。
Docker Desktop 本地测试可使用 `host.docker.internal` 访问宿主机映射的资产端口。

以下连接参数已在 Core 中提供默认值，标准 installer 部署无需重复配置。
自定义部署可在 Core/Celery 的 `config.yml` 中覆盖，并重启相关进程：

```yaml
ANSIBLE_DOCKER_ENABLED: true
ANSIBLE_EXECUTOR_HOST: ansible-executor
ANSIBLE_EXECUTOR_PORT: 2222
ANSIBLE_EXECUTOR_PRIVATE_KEY: /run/jms-executor/client
ANSIBLE_EXECUTOR_KNOWN_HOSTS: /run/jms-executor/known_hosts
ANSIBLE_EXECUTOR_CONNECT_TIMEOUT: 10
# 使用网域 SSH 隧道时，必须填执行容器可访问的当前 Core/Celery 节点地址。
# ANSIBLE_EXECUTOR_GATEWAY_HOST: celery-ansible
```

installer 通过 `env_file` 传入自定义连接参数，Compose 仅分别指定 Core/Celery 的网域隧道地址。
连接参数的读取优先级为 `config.yml`、环境变量、Core 默认值。

系统设置 > 功能设置 > 作业中心的「Ansible Docker 隔离」沿用原字段和已保存的值，
无需迁移。开启使用 `jumpserver/ansible-executor` 常驻容器；关闭后本地执行，
不再获得执行容器的 UID 和文件隔离。执行器连接失败会报错，不自动降级到本地。
实验性配置 `ANSIBLE_EXECUTION_BACKEND` 已移除，不再覆盖这个开关。
旧 `jumpserver/ansible-executor` 逐任务 Docker 执行方式已停用，不能只替换旧镜像的标签；
需按上文部署常驻 SSH 服务。旧镜像构建文件仅保留为历史参考，不再自动构建发布。
部署这个后端时还需更新 Python 依赖（`uv sync --frozen`）。

任务通过 Runner transmit/worker 流协议传输，不使用 SFTP。上传文件、生成的
inventory、资产私钥/证书、自定义模块和模块工具都必须在任务私有目录内；
系统自动生成的凭据（包括切换账号使用的 `su_from` 私钥）已使用此布局。
SSH 包装脚本在任务的私有临时目录创建锁，避免不同 UID 共用锁文件而被拒绝访问。
密码网关通过 `sshpass -f` 读取任务目录内的 `0600` 文件，密码不再出现在
SSH/sshpass 命令行中。账号模块读取同一文件；远端按任务 UID 隔离访问并在会话结束后清理。
远端只迁移已知的执行路径，保留用户业务值和
上传目的地址。项目 symlink / 特殊文件会被拒绝，输入文件总量上限为 128 MiB；
大型上传需要另行设计分块传输。服务私钥和 Core 的其他目录不会自动打包。

## 生命周期与取消

每个任务建立独立 SSH 连接并随机选择虚拟 UID。服务端 PAM session 模块持有
该 UID 的独占文件锁，拿到服务端确认后客户端才发送任务内容。相同 UID 并发
登录会被拒绝；客户端遇到忙身份会尝试其他编号，最多 16 次。

会话结束或断开后，由 sshd 的 root PAM 进程清理该 UID 的全部残留进程、家目录
及镜像内公共临时目录中的 UID 所属文件。登录前再做一次恢复清理，处理上次
monitor 崩溃的情况。清理失败时拒绝复用。不要挂载额外的任务可写共享卷；
派生镜像新增公共可写目录时也必须扩展清理策略。

状态、任务事件和 rc 进入原回调。Core 不将远端 PID 写成 `local.pid`，避免误杀
本机进程。停止请求使用任务 UUID：保留 Redis 通知，同时在共享任务目录写取消
标记，兼容 Celery prefork 子进程。客户端定期检查取消/超时并关闭 SSH 连接，
服务端再回收 UID。认证/连接阶段的响应时间受 connect timeout 限制。

沿用 `ANSIBLE_RUNNER_JOB_TIMEOUT`，显式任务 timeout 优先。Celery ansible 队列的
worker 并发数控制调度并发；增加 Celery worker 时需按执行容器容量限制总并发。
一个常驻执行容器可处理多个不同 UID 的任务，无需每个任务启动容器。

## 兼容范围

已验证上游 Runner 2.4.0、Core Runner 2.4.0.2 客户端与执行端 Core Runner 2.4.0.2
的流兼容，覆盖 AdHoc、Playbook、文件上传、自定义模块、事件流、失败 rc、取消和超时，
并通过真实 Celery 账号发现、Linux 账号推送、改密/换钥和校验流程验证，
包括密钥登录后切换账号、网关私钥和并发任务场景。日志保留 Ansible 的 ANSI 颜色。
执行镜像使用 `requirements-runtime.txt` 提供业务所需的 Python 驱动和 Collections；
升级 Ansible 或业务依赖后仍需回归对应 Playbook。

这是同一 Linux 容器内的多 UID 隔离，共享内核、网络和整体资源上限。其他 UID
通常仍能看到进程名称/命令行，秘密必须通过私有文件或环境传递。localhost 服务
需要自身认证。任务间没有单独 PID/network namespace 或 cgroup。

## 验证

`apps/ops/tests/test_ansible_ssh.py` 提供后端选择、原回调、取消和路径边界测试。
`apps/accounts/tests/test_ansible_credential_paths.py` 覆盖切换账号的私钥与 SSH 锁路径。
`apps/ops/tests/test_gateway_credentials.py` 覆盖网关密码文件权限、特殊字符和账号模块兼容。
端到端用例默认跳过；对一个专用临时 executor 设置以下变量即可运行：

```sh
export JMS_EXECUTOR_TEST_HOST=127.0.0.1
export JMS_EXECUTOR_TEST_PORT=2222
export JMS_EXECUTOR_TEST_KEY=/absolute/path/to/test-client
export JMS_EXECUTOR_TEST_KNOWN_HOSTS=/absolute/path/to/test-known_hosts
python apps/manage.py test ops.tests.test_ansible_docker ops.tests.test_ansible_ssh accounts.tests.test_ansible_credential_paths
```

端到端测试会执行 localhost 作业，只能指向测试执行容器。executor 仓库另有真实
sshd 隔离、UID 回收和恶意事件/归档测试及 CI。
