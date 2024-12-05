<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.org/index-en.html"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## 什么是 JumpServer？

JumpServer 是一个开源的特权访问管理 (PAM) 工具，提供给 DevOps 和 IT 团队通过网络浏览器按需安全访问 SSH、RDP、Kubernetes、数据库和 RemoteApp 终端。

![JumpServer 概述](https://github.com/jumpserver/jumpserver/assets/32935519/35a371cb-8590-40ed-88ec-f351f8cf9045)

## 快速开始

准备一个干净的 Linux 服务器 ( 64 位，>= 4c8g )

```sh
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

在浏览器中访问 JumpServer `http://your-jumpserver-ip/`
- 用户名：`admin`
- 密码：`ChangeMe`

[![JumpServer 快速开始](https://github.com/user-attachments/assets/0f32f52b-9935-485e-8534-336c63389612)](https://www.youtube.com/watch?v=UlGYRbKrpgY "JumpServer 快速开始")

## 截图

<table style="border-collapse: collapse; border: 1px solid black;">
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/99fabe5b-0475-4a53-9116-4c370a1426c4" alt="JumpServer 控制台"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/a424d731-1c70-4108-a7d8-5bbf387dda9a" alt="JumpServer 审计"   /></td>
  </tr>

  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/393d2c27-a2d0-4dea-882d-00ed509e00c9" alt="JumpServer 工作台"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/3a2611cd-8902-49b8-b82b-2a6dac851f3e" alt="JumpServer 设置"   /></td>
  </tr>

  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/1e236093-31f7-4563-8eb1-e36d865f1568" alt="JumpServer SSH"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/69373a82-f7ab-41e8-b763-bbad2ba52167" alt="JumpServer RDP"   /></td>
  </tr>
  <tr>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/5bed98c6-cbe8-4073-9597-d53c69dc3957" alt="JumpServer K8s"   /></td>
    <td style="padding: 5px;background-color:#fff;"><img src= "https://github.com/jumpserver/jumpserver/assets/32935519/b80ad654-548f-42bc-ba3d-c1cfdf1b46d6" alt="JumpServer 数据库"   /></td>
  </tr>
</table>

## 组件

JumpServer 由多个关键组件组成，这些组件共同构成了 JumpServer 的功能框架，为用户提供全面的运维管理和安全控制能力。

| 项目                                                  | 状态                                                                                                                                                                  | 描述                                                                                                |
|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)           | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina 发布" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | JumpServer Web 用户界面                                                                               |
| [Luna](https://github.com/jumpserver/luna)           | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna 发布" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | JumpServer Web 终端                                                                                 |
| [KoKo](https://github.com/jumpserver/koko)           | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko 发布" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | JumpServer 字符协议连接器                                                                             |
| [Lion](https://github.com/jumpserver/lion)           | <a href="https://github.com/jumpserver/lion/releases"><img alt="Lion 发布" src="https://img.shields.io/github/release/jumpserver/lion.svg" /></a>                   | JumpServer 图形协议连接器                                                                             |
| [Chen](https://github.com/jumpserver/chen)           | <a href="https://github.com/jumpserver/chen/releases"><img alt="Chen 发布" src="https://img.shields.io/github/release/jumpserver/chen.svg" />                       | JumpServer Web 数据库                                                                                 |  
| [Razor](https://github.com/jumpserver/razor)         | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                             | JumpServer EE RDP 代理连接器                                                                          |
| [Tinker](https://github.com/jumpserver/tinker)       | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                           | JumpServer EE 远程应用连接器 (Windows)                                                                  |
| [Panda](https://github.com/jumpserver/Panda)         | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                           | JumpServer EE 远程应用连接器 (Linux)                                                                    |
| [Magnus](https://github.com/jumpserver/magnus)       | <img alt="Magnus" src="https://img.shields.io/badge/release-private-red" />                                                                                           | JumpServer EE 数据库代理连接器                                                                         |
| [Nec](https://github.com/jumpserver/nec)             | <img alt="Nec" src="https://img.shields.io/badge/release-private-red" />                                                                                              | JumpServer EE VNC 代理连接器                                                                          |
| [Facelive](https://github.com/jumpserver/facelive)   | <img alt="Facelive" src="https://img.shields.io/badge/release-private-red" />                                                                                         | JumpServer EE 面部识别                                                                                 |


## 贡献

欢迎提交 PR 进行贡献。请参考 [CONTRIBUTING.md][contributing-link] 获取指南。

## 安全

JumpServer 是一个关键任务产品。请参考安装和部署的基本安全建议。如果您遇到任何与安全相关的问题，请直接联系我们：

- 邮箱：support@fit2cloud.com

## License

Copyright (c) 2014-2024 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3) (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an " AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

<!-- JumpServer official link -->
[docs-link]: https://jumpserver.com/docs
[discord-link]: https://discord.com/invite/W6vYXmAQG2
[contributing-link]: https://github.com/jumpserver/jumpserver/blob/dev/CONTRIBUTING.md

<!-- JumpServer Other link-->
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[docker-link]: https://hub.docker.com/u/jumpserver
[github-release-link]: https://github.com/jumpserver/jumpserver/releases/latest
[github-stars-link]: https://github.com/jumpserver/jumpserver
[github-issues-link]: https://github.com/jumpserver/jumpserver/issues

<!-- Shield link-->
[github-release-shield]: https://img.shields.io/github/v/release/jumpserver/jumpserver
[github-stars-shield]: https://img.shields.io/github/stars/jumpserver/jumpserver?color=%231890FF&style=flat-square
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jms_all.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[discord-shield]: https://img.shields.io/discord/1194233267294052363?style=flat&logo=discord&logoColor=%23f5f5f5&labelColor=%235462eb&color=%235462eb