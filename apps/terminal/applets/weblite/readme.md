# JumpServer WebLite

独立 Electron Web applet，由 Tinker 启动，使用与客户端相同的账号代填、脚本、交互区域和成功 selector。

默认直接访问资产，登录信息由 Tinker 通过启动管道传入，无需 Koko Web Proxy，继续使用 RemoteApp 的 RDP 录像。需要支持原生 applet 的 Tinker（Core 部署清单当前使用候选版本 v0.3.0），并确保发布机能访问资产及 SSO 网站。

发布机部署选项中的 Web applet recording 默认关闭。启用时需填写 Koko Web Proxy 地址，产生独立的额外 Web 录像；RDP 录像保留。

当前支持同一窗口主页面的登录流程；旧 Chrome 脚本的 select_frame 和独立弹窗尚不支持。

构建源码位于 Luna 的 applets/weblite，安装包包含完整浏览器运行时。

发布机通过 `tinkerd install` 执行 `setup.yml`，使用 Windows Installer 静默安装
`JumpServer-WebLite-5.0.0-beta18-x64.msi`，不再解压浏览器 ZIP。
MSI 安装到 `%ProgramFiles%\JumpServer\WebLite`，供发布机上的所有用户使用。
安装包需同步到 Core 下载服务的 `/download/applets/`，以便通过 `jms:///` 下载。
上游安装包：[Luna v5.0.0-beta18](https://github.com/jumpserver/luna/releases/download/v5.0.0-beta18/JumpServer-WebLite-5.0.0-beta18-x64.msi)。

需要配套支持 `%ProgramFiles%/JumpServer/` 路径的 Tinker。清单直接启动
`app-5.0.0-beta18/weblite.exe`，以保留启动管道和进程生命周期；根目录的
`weblite.exe` 是 MSI 生成的启动器。升级时同时更新清单版本、版本目录和安装/卸载包名。
卸载时通过保留在 applet 目录内的 MSI 执行 Windows Installer 卸载。
