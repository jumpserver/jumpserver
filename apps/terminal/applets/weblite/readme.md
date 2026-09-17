# JumpServer WebLite

独立 Electron Web applet，由 Tinker 启动，使用与客户端相同的账号代填、脚本、交互区域和成功 selector。

清单通过 `exec_type: exe` 和 `stdin: true` 声明启动方式。Tinker 消费连接令牌后，通过标准输入发送通用 `AppletArgs` JSON（资产、账号、平台等原始连接数据），不识别 WebLite 名称或转换登录配置。WebLite 自行解析资产地址、选择资产或平台登录配置、处理匿名账号并执行代填；关闭代填时仍自动打开资产地址。

WebLite 直接访问资产，不与 Koko 通信，录像由 RemoteApp 的 RDP 会话负责。发布机需安装支持清单 `stdin: true` 的 Tinker 和通用连接参数的 WebLite，并同步更新本清单；Core 部署清单中的旧版本号不保证包含此能力。发布机需能访问资产及 SSO 网站。

发布机和 Tinker 不需要配置 Web Proxy 地址或 Web 录像开关，旧配置中的这些选项不再生效。

当前支持同一窗口主页面的登录流程；旧 Chrome 脚本的 select_frame 和独立弹窗尚不支持。

构建源码位于 Luna 的 applets/weblite，安装包包含完整浏览器运行时。

发布机通过 `tinkerd install` 执行 `setup.yml`，使用 Windows Installer 静默安装
`JumpServer-WebLite-5.0.0-x64.msi`，不再解压浏览器 ZIP。
MSI 将完整运行时直接安装到 `%ProgramFiles%\JumpServer\WebLite`，供发布机上的所有用户使用。
安装包需同步到 Core 下载服务的 `/download/applets/`，以便通过 `jms:///` 下载。
上游安装包：[Luna v5.0.0](https://github.com/jumpserver/luna/releases/download/v5.0.0/JumpServer-WebLite-5.0.0-x64.msi)。

需要配套支持 `%ProgramFiles%/JumpServer/` 路径的 Tinker。清单直接启动
`%ProgramFiles%/JumpServer/WebLite/weblite.exe`，以保留启动管道和进程生命周期。
该路径是实际的 Electron 程序，安装目录内只有一个 `weblite.exe`，没有版本子目录和额外启动器。
升级时只需更新清单版本和安装/卸载包名，可执行文件路径保持不变。
本清单必须与新版扁平目录 MSI 一起部署；旧 MSI 的根目录仍是启动器。升级前关闭所有 WebLite 会话。
卸载时通过保留在 applet 目录内的 MSI 执行 Windows Installer 卸载。
