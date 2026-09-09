# JumpServer WebLite

独立 Electron Web applet，由 Tinker 启动，使用与客户端相同的账号代填、脚本、交互区域和成功 selector。

默认直接访问资产，登录信息由 Tinker 通过启动管道传入，无需 Koko Web Proxy，继续使用 RemoteApp 的 RDP 录像。需要支持原生 applet 的 Tinker（Core 部署清单当前使用候选版本 v0.3.0），并确保发布机能访问资产及 SSO 网站。

发布机部署选项中的 Web applet recording 默认关闭。启用时需填写 Koko Web Proxy 地址，产生独立的额外 Web 录像；RDP 录像保留。

当前支持同一窗口主页面的登录流程；旧 Chrome 脚本的 select_frame 和独立弹窗尚不支持。

构建源码位于 Luna 的 applets/weblite，安装包包含完整浏览器运行时。
