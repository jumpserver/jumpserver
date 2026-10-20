# SSH Ansible executor

Core 支持 `native`、`docker` 和 `ssh` 三种执行方式。SSH 后端复用现有
AdHocRunner、PlaybookRunner、SuperPlaybookRunner、UploadFileRunner 和回调；
Celery 将任务目录传给常驻的 OpenSSH 执行容器，任务以独立 UID 运行。
Core/Celery 不需要 Docker socket，也不会调用本地 bwrap。SDK 源码和服务端在
[jumpserver/ansible-executor](https://github.com/jumpserver/ansible-executor)。

## 配置

先按[配套 executor 说明](https://github.com/jumpserver/ansible-executor/blob/d9406056475266a3342fa86be152435930ac1342/README.md)
构建并启动镜像，使用与 SDK 锁定版本一致的 `d9406056475266a3342fa86be152435930ac1342`
提交，生成每套部署独立的服务密钥。
执行容器所在 Linux 内核及 seccomp 策略需要允许 `pidfd_open` 和
`pidfd_send_signal`；不支持时服务端会拒绝创建会话。sshd 需要容器内 root，
无需 privileged、SYS_ADMIN 或宿主机 PID namespace。
将公钥挂载给 executor，只将私钥及可信取得的服务器 host key 挂载给 Celery。
私钥不要放进任务目录、Playbook 或环境变量。`known_hosts` 中必须使用实际连接
地址；非 22 端口的格式是 `[ansible-executor]:2222 ssh-ed25519 ...`。

在 Core/Celery 的 `config.yml` 中配置，并重启相关进程：

```yaml
ANSIBLE_EXECUTION_BACKEND: ssh
ANSIBLE_EXECUTOR_HOST: ansible-executor
ANSIBLE_EXECUTOR_PORT: 2222
ANSIBLE_EXECUTOR_PRIVATE_KEY: /run/secrets/executor_client
ANSIBLE_EXECUTOR_KNOWN_HOSTS: /run/secrets/executor_known_hosts
ANSIBLE_EXECUTOR_CONNECT_TIMEOUT: 10
# 使用 Core 上的网域 SSH 隧道时，必须填执行容器可访问的 Celery 地址。
# ANSIBLE_EXECUTOR_GATEWAY_HOST: celery-ansible
```

`ANSIBLE_EXECUTION_BACKEND` 留空时继续按原 `ANSIBLE_DOCKER_ENABLED` 设置运行。
显式配置 `ssh` 优先于该旧设置。设置 `native` 或 `docker` 可直接切回原执行方式。
部署这个后端时还需更新 Python 依赖（`uv sync --frozen`）。

任务通过 Runner transmit/worker 流协议传输，不使用 SFTP。上传文件、生成的
inventory、资产私钥/证书、自定义模块和模块工具都必须在任务私有目录内；
系统自动生成的凭据已使用此布局。远端只迁移已知的执行路径，保留用户业务值和
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

已验证 Core 的 Runner 2.4.0.2 与执行端上游 Runner 2.4.0 的流兼容，覆盖 AdHoc、
Playbook、文件上传、自定义模块、事件流、失败 rc、取消和超时。
通用执行镜像提供 Ansible 内置模块。数据库、WinRM 等业务需要的 Python 驱动、
collections 及系统依赖请安装到派生镜像；升级 Ansible 后需要回归业务 Playbook。

这是同一 Linux 容器内的多 UID 隔离，共享内核、网络和整体资源上限。其他 UID
通常仍能看到进程名称/命令行，秘密必须通过私有文件或环境传递。localhost 服务
需要自身认证。任务间没有单独 PID/network namespace 或 cgroup。

## 验证

`apps/ops/tests/test_ansible_ssh.py` 提供后端选择、原回调、取消和路径边界测试。
端到端用例默认跳过；对一个专用临时 executor 设置以下变量即可运行：

```sh
export JMS_EXECUTOR_TEST_HOST=127.0.0.1
export JMS_EXECUTOR_TEST_PORT=2222
export JMS_EXECUTOR_TEST_KEY=/absolute/path/to/test-client
export JMS_EXECUTOR_TEST_KNOWN_HOSTS=/absolute/path/to/test-known_hosts
python apps/manage.py test ops.tests.test_ansible_docker ops.tests.test_ansible_ssh
```

端到端测试会执行 localhost 作业，只能指向测试执行容器。executor 仓库另有真实
sshd 隔离、UID 回收和恶意事件/归档测试及 CI。
