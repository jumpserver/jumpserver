# 客户端文档维护

SDK 编程语言为 Python、Go、Java 和 Node.js；cURL 保留为协议调试脚本。文档语言跟随界面语言。

文档覆盖 `en`、`zh-hans`、`zh-hant`、`ja`、`ko`、`pt-br`、`ru`、`vi`、`es`、`fr`。服务端将界面语言别名规范化为文件名，未知语言回退到英文。

- Python 的英文与简体中文 README 是完整参考文档，直接维护。
- 其他语言的 Python 接入指南、Go/Java/Node.js SDK 指南和 cURL 调试指南从 `translations/*.json` 生成。
- SDK 功能以 Python 为准。Go、Java、Node.js 采用相同章节和流程，按各语言习惯命名方法与响应字段。
- 方法映射、运行命令、配置字段在 `build.py` 中统一维护；原生 SDK 的取密与事件示例直接读取各语言的可编译示例源码，翻译仅修改正文。
- 事件处理、最新凭据保留及重连说明也由 `build.py` 和翻译文件生成；新增钩子示例同时维护 `HOOK_EXAMPLES`，强制实时取密与本地来源标记维护在 `LATEST_CREDENTIAL_APIS`。
- 文档中心读取各目录的 `README.<locale>.md`，不在请求过程中生成或翻译文档。

从仓库根目录生成并检查：

```bash
python3 apps/accounts/clients/docs/build.py
python3 apps/accounts/clients/docs/build.py --check
```

变更 SDK 时同步更新服务端 `credential_client/documentation.py` 的运行环境、示例文件、安装命令及能力标记。应用接入向导复用这里的语言清单和事件示例，并另外生成当前应用的身份配置。新增公共方法须同步四种 SDK、方法映射和协议测试；新增协议功能须明确旧客户端兼容行为。

## 协议验证

安装 Node.js SDK 的依赖后，运行共享 HTTP/WebSocket 契约测试。测试服务检查精确请求体摘要、签名头顺序、URL 编码、请求 ID、版本头、事件回执和重新签名，覆盖四种 SDK 的取密、确认、同步、指令与事件生命周期。

```bash
npm ci --prefix apps/accounts/clients/node
python3 apps/accounts/clients/tests/run.py
```

需要 Go、Java、Maven、Node.js，以及已安装 Python SDK 的 Python 环境；可用 `JMS_MAVEN` 指定 Maven 路径。测试使用本地协议服务，实际应用连接切换和 Core 联调需在目标环境另行验证。

## Go Agent

独立 Agent 入口为 `go/cmd/jms-pam-agent`，配置和交付说明位于 `go/agent/README.*.md`。Python 包只提供 SDK，运行 Agent 不需要 Python。服务名称固定为 `jms-pam-agent`；生成文档不得拼接 configuration ID 作为服务名。Agent 文档通过翻译键 `agent_setup`、`agent_rules`、`native_agent` 等维护。
