<div align="center">
  <a name="readme-top"></a>
  <a href="https://jumpserver.org"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
  
## An open-source PAM tool（Bastion Host）

[![][license-shield]][license-link]
[![][docker-shield]][docker-link]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]

**English** · [简体中文](./README.zh-CN.md) · [Documents][docs-link] · [Report Bug][github-issues-link] · [Request Feature][github-issues-link]
</div>
<br/>

## What is JumpServer?

JumpServer is an open source Privileged Access Management (PAM) tool that provides DevOps and IT teams with instant and secure access to SSH, RDP, K8s, Database endpoints through a web browser.

TBD: 6 sceenshots(登录、首页、Linux、Windows、Database、K8s、录像审计)

## Quick Start
<!-- 只提供环境要求信息、一键安装脚本及登录信息 -->

Prepare a Linux Server ( >4c8g )

```
curl -sSL https://github.com/jumpserver/jumpserver/releases/latest/download/quick_start.sh | bash
```

Access JumpServer in your browser at `http://ip:port/`, `admin`/`admin`

## Components

JumpServer consists of multiple key components, which collectively form the functional framework of JumpServer, providing users with comprehensive capabilities for operations management and security control.

| Project                                                | Status                                                                                                                                                                 | Description                                                                                             |
|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| [Lina](https://github.com/jumpserver/lina)             | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina release" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a>                   | JumpServer Web UI                                                                                       |
| [Luna](https://github.com/jumpserver/luna)             | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna release" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a>                   | JumpServer Web Terminal                                                                                 |
| [KoKo](https://github.com/jumpserver/koko)             | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko release" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a>                   | JumpServer Character Protocol Connector                                                                 |
| [Lion](https://github.com/jumpserver/lion-release)     | <a href="https://github.com/jumpserver/lion-release/releases"><img alt="Lion release" src="https://img.shields.io/github/release/jumpserver/lion-release.svg" /></a>   | JumpServer Graphical Protocol Connector                                                                 |
| [Razor](https://github.com/jumpserver/razor)           | <img alt="Chen" src="https://img.shields.io/badge/release-private-red" />                                                                                              | JumpServer RDP Proxy Connector                                                                          |
| [Tinker](https://github.com/jumpserver/tinker)         | <img alt="Tinker" src="https://img.shields.io/badge/release-private-red" />                                                                                            | JumpServer Remote Application Connector (Windows)                                                       |
| [Panda](https://github.com/jumpserver/Panda)           | <img alt="Panda" src="https://img.shields.io/badge/release-private-red" />                                                                                             | JumpServer Remote Application Connector (Linux)                                                         |
| [Magnus](https://github.com/jumpserver/magnus-release) | <a href="https://github.com/jumpserver/magnus-release/releases"><img alt="Magnus release" src="https://img.shields.io/github/release/jumpserver/magnus-release.svg" /> | JumpServer Database Proxy Connector                                                                     |
| [Chen](https://github.com/jumpserver/chen-release)     | <a href="https://github.com/jumpserver/chen-release/releases"><img alt="Chen release" src="https://img.shields.io/github/release/jumpserver/chen-release.svg" />       | JumpServer Web DB                                                                                       |
| [Kael](https://github.com/jumpserver/kael)             | <a href="https://github.com/jumpserver/kael/releases"><img alt="Kael release" src="https://img.shields.io/github/release/jumpserver/kael.svg" />                       | JumpServer GPT Assets Connector                                                                         |
| [Wisp](https://github.com/jumpserver/wisp)             | <a href="https://github.com/jumpserver/wisp/releases"><img alt="Magnus release" src="https://img.shields.io/github/release/jumpserver/wisp.svg" />                     | JumpServer Inter-Project Communication Component with Core API                                          |
| [Clients](https://github.com/jumpserver/clients)       | <a href="https://github.com/jumpserver/clients/releases"><img alt="Clients release" src="https://img.shields.io/github/release/jumpserver/clients.svg" />              | JumpServer Client                                                                                       |
| [Installer](https://github.com/jumpserver/installer)   | <a href="https://github.com/jumpserver/installer/releases"><img alt="Installer release" src="https://img.shields.io/github/release/jumpserver/installer.svg" />        | JumpServer Installation Tool                                                                            |

## Contributing

Welcome to submit PR to contribute. Please refer to [CONTRIBUTING.md][contributing-link] for guidelines.

## Security

JumpServer is a secure product. Please refer to the Basic Security Recommendations for installation and deployment. If you encounter any security-related issues, please contact us directly:

- Email: ibuler@fit2cloud.com

## License

Copyright (c) 2014-2024 飞致云 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3) (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an " AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

<!-- JumpServer official link -->
[official-website-en-link]: https://jumpserver.org/
[docs-link]: https://docs.jumpserver.org/
[community-link]: https://community.fit2cloud.com/#/products/jumpserver/downloads
[demo-link]: https://demo.jumpserver.org/
[discord-link]: https://discord.gg/DVz6Hckx
[contributing-link]: https://github.com/jumpserver/jumpserver/blob/dev/CONTRIBUTING.md

<!-- JumpServer Other link-->
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[docker-link]: https://hub.docker.com/u/jumpserver
[github-release-shield]: https://img.shields.io/github/v/release/jumpserver/jumpserver
[github-release-link]: https://github.com/jumpserver/jumpserver/releases/latest
[github-stars-shield]: https://img.shields.io/github/stars/jumpserver/jumpserver?color=%231890FF&style=flat-square
[github-stars-link]: https://github.com/jumpserver/jumpserver
[github-issues-link]: https://github.com/jumpserver/jumpserver/issues
[github-trending-link]: https://trendshift.io/repositories/5071

<!-- Shield link-->
[docker-shield]: https://img.shields.io/docker/pulls/jumpserver/jms_all.svg
[license-shield]: https://img.shields.io/github/license/jumpserver/jumpserver
[demo-shield-badge]: https://img.shields.io/badge/ONLINE-online?style=plastic&logo=jameson&logoColor=white&label=TRY%20JUMPSERVER&labelColor=black&color=%23148f76
[discord-shield-badge]: https://img.shields.io/badge/JOIN_US_NOW-ONLINE?style=plastic&logo=discord&logoColor=white&label=DISCORD&labelColor=black&color=%23404eed
[version-ee-shield-badge]: https://img.shields.io/badge/Enterprise-black?style=flat-square&logo=vagrant
[github-trending-shield]: https://trendshift.io/api/badge/repositories/5071

<!-- Image link -->
[image-jumpserver]: https://download.jumpserver.org/images/jumpserver-logo.svg
[image-dashboard]: https://github.com/jumpserver/jumpserver/assets/32935519/014c2230-82d3-4b53-b907-8149ce44bbd0
[image-star]: https://github.com/jumpserver/jumpserver/assets/32935519/76158e65-783d-4f11-81cd-45556a388e63
[image-supported-asset-type]: https://github.com/jumpserver/jumpserver/assets/32935519/8e769007-5449-4e86-b34b-d04e8e484257
[image-system-architecture]: https://github.com/jumpserver/jumpserver/assets/32935519/8a720b4e-19ed-4e3c-a8aa-325d7581005a
