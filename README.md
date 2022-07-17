<p align="center">
  <a href="https://jumpserver.org"><img src="https://download.jumpserver.org/images/jumpserver-logo.svg" alt="JumpServer" width="300" /></a>
</p>
<h3 align="center">多云环境下更好用的堡垒机</h3>

<p align="center">
  <a href="https://www.gnu.org/licenses/gpl-3.0.html"><img src="https://img.shields.io/github/license/jumpserver/jumpserver" alt="License: GPLv3"></a>
  <a href="https://shields.io/github/downloads/jumpserver/jumpserver/total"><img src="https://shields.io/github/downloads/jumpserver/jumpserver/total" alt=" release"></a>
  <a href="https://hub.docker.com/u/jumpserver"><img src="https://img.shields.io/docker/pulls/jumpserver/jms_all.svg" alt="Codacy"></a>
  <a href="https://github.com/jumpserver/jumpserver/commits"><img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/jumpserver/jumpserver.svg" /></a>
  <a href="https://github.com/jumpserver/jumpserver"><img src="https://img.shields.io/github/stars/jumpserver/jumpserver?color=%231890FF&style=flat-square" alt="Stars"></a>
</p>

--------------------------
- [ENGLISH](https://github.com/jumpserver/jumpserver/blob/master/README_EN.md)



JumpServer 是全球首款开源的堡垒机，使用 GPLv3 开源协议，是符合 4A 规范的运维安全审计系统。

JumpServer 使用 Python 开发，配备了业界领先的 Web Terminal 方案，交互界面美观、用户体验好。

JumpServer 采纳分布式架构，支持多机房跨区域部署，支持横向扩展，无资产数量及并发限制。

改变世界，从一点点开始 ...

> 如需进一步了解 JumpServer 开源项目，推荐阅读 [JumpServer 的初心和使命](https://mp.weixin.qq.com/s/S6q_2rP_9MwaVwyqLQnXzA)

### 特色优势

- 开源: 零门槛，线上快速获取和安装；
- 分布式: 轻松支持大规模并发访问；
- 无插件: 仅需浏览器，极致的 Web Terminal 使用体验；
- 多租户: 一套系统，多个子公司或部门同时使用；
- 多云支持: 一套系统，同时管理不同云上面的资产；
- 云端存储: 审计录像云端存储，永不丢失；
- 多应用支持: 数据库，Windows远程应用，Kubernetes。

### UI 展示

![UI展示](https://www.jumpserver.org/images/screenshot/1.png)

### 在线体验

-   环境地址：<https://demo.jumpserver.org/>

| :warning: 注意                 |
| :--------------------------- |
| 该环境仅作体验目的使用，我们会定时清理、重置数据！    |
| 请勿修改体验环境用户的密码！               |
| 请勿在环境中添加业务生产环境地址、用户名密码等敏感信息！ |

### 快速开始

- [极速安装](https://docs.jumpserver.org/zh/master/install/setup_by_fast/)
- [完整文档](https://docs.jumpserver.org)
- [演示视频](https://www.bilibili.com/video/BV1ZV41127GB)
- [手动安装](https://github.com/jumpserver/installer)

### 组件项目
| 项目                                                                          |  状态          | 描述                                     |
| ---------------------------------------------------------------------------  |  -------------------   | ---------------------------------------- |
| [Lina](https://github.com/jumpserver/lina) | <a href="https://github.com/jumpserver/lina/releases"><img alt="Lina release" src="https://img.shields.io/github/release/jumpserver/lina.svg" /></a> | JumpServer Web UI 项目 |
| [Luna](https://github.com/jumpserver/luna) | <a href="https://github.com/jumpserver/luna/releases"><img alt="Luna release" src="https://img.shields.io/github/release/jumpserver/luna.svg" /></a> | JumpServer Web Terminal 项目 |
| [KoKo](https://github.com/jumpserver/koko) | <a href="https://github.com/jumpserver/koko/releases"><img alt="Koko release" src="https://img.shields.io/github/release/jumpserver/koko.svg" /></a> | JumpServer 字符协议 Connector 项目，替代原来 Python 版本的 [Coco](https://github.com/jumpserver/coco) |
| [Lion](https://github.com/jumpserver/lion-release) | <a href="https://github.com/jumpserver/lion-release/releases"><img alt="Lion release" src="https://img.shields.io/github/release/jumpserver/lion-release.svg" /></a>  | JumpServer 图形协议 Connector 项目，依赖 [Apache Guacamole](https://guacamole.apache.org/) |
| [Magnus](https://github.com/jumpserver/magnus-release) | <a href="https://github.com/jumpserver/magnus-release/releases"><img alt="Magnus release" src="https://img.shields.io/github/release/jumpserver/magnus-release.svg" /> | JumpServer 数据库代理 Connector 项目 |
| [Clients](https://github.com/jumpserver/clients) | <a href="https://github.com/jumpserver/clients/releases"><img alt="Clients release" src="https://img.shields.io/github/release/jumpserver/clients.svg" /> | JumpServer 客户端 项目 |
| [Installer](https://github.com/jumpserver/installer)| <a href="https://github.com/jumpserver/installer/releases"><img alt="Installer release" src="https://img.shields.io/github/release/jumpserver/installer.svg" /> | JumpServer 安装包 项目 |

### 社区

如果您在使用过程中有任何疑问或对建议，欢迎提交 [GitHub Issue](https://github.com/jumpserver/jumpserver/issues/new/choose) 或加入到我们的社区当中进行进一步交流沟通。

#### 微信交流群

<img src="https://download.jumpserver.org/images/wecom-group.jpeg" alt="微信群二维码" width="200"/>

### 贡献
如果有你好的想法创意，或者帮助我们修复了 Bug, 欢迎提交 Pull Request

感谢以下贡献者，让 JumpServer 更加完善

<a href="https://github.com/jumpserver/jumpserver/graphs/contributors"><img src="https://opencollective.com/jumpserver/contributors.svg?width=890&button=false" /></a>



### 致谢
- [Apache Guacamole](https://guacamole.apache.org/) Web页面连接 RDP, SSH, VNC 协议设备，JumpServer 图形化组件 Lion 依赖 
- [OmniDB](https://omnidb.org/) Web 页面连接使用数据库，JumpServer Web 数据库依赖


### JumpServer 企业版 
- [申请企业版试用](https://jinshuju.net/f/kyOYpi)

### 案例研究

- [JumpServer 堡垒机护航顺丰科技超大规模资产安全运维](https://blog.fit2cloud.com/?p=1147)
- [JumpServer 堡垒机让“大智慧”的混合 IT 运维更智慧](https://blog.fit2cloud.com/?p=882)
- [携程 JumpServer 堡垒机部署与运营实战](https://blog.fit2cloud.com/?p=851)
- [小红书的JumpServer堡垒机大规模资产跨版本迁移之路](https://blog.fit2cloud.com/?p=516)
- [JumpServer堡垒机助力中手游提升多云环境下安全运维能力](https://blog.fit2cloud.com/?p=732)
- [中通快递：JumpServer主机安全运维实践](https://blog.fit2cloud.com/?p=708)
- [东方明珠：JumpServer高效管控异构化、分布式云端资产](https://blog.fit2cloud.com/?p=687)
- [江苏农信：JumpServer堡垒机助力行业云安全运维](https://blog.fit2cloud.com/?p=666)

### 安全说明

JumpServer是一款安全产品，请参考 [基本安全建议](https://docs.jumpserver.org/zh/master/install/install_security/) 部署安装.

如果你发现安全问题，可以直接联系我们：

- ibuler@fit2cloud.com 
- support@fit2cloud.com 
- 400-052-0755

### License & Copyright

Copyright (c) 2014-2022 飞致云 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 3 (GPLv3)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-3.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
