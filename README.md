# Jumpserver 多云环境下更好用的堡垒机

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.1-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Ansible](https://img.shields.io/badge/ansible-2.4.2.0-blue.svg?style=plastic)](https://www.ansible.com/)
[![Paramiko](https://img.shields.io/badge/paramiko-2.4.1-green.svg?style=plastic)](http://www.paramiko.org/)

Jumpserver 是全球首款完全开源的堡垒机，使用 GNU GPL v2.0 开源协议，是符合 4A 机制的运维安全审计系统。

Jumpserver 使用 Python / Django 进行开发，遵循 Web 2.0 规范，配备了业界领先的 Web Terminal 方案，交互界面美观、用户体验好。

Jumpserver 采纳分布式架构，支持多机房跨区域部署，支持横向扩展，无资产数量及并发限制。

改变世界，从一点点开始。

注: [KubeOperator](https://github.com/KubeOperator/KubeOperator) 是 Jumpserver 团队在 Kubernetes 领域的的又一全新力作，欢迎关注和使用。

## 核心功能列表

<table>
  <tr>
    <th rowspan="7">身份认证</th>
    <th rowspan="4">登录认证</th>
    <th>资源统一登录与认证</th>
  </tr>
  <tr>
    <td>LDAP/AD 认证</td>
  </tr>
  <tr>
    <td>RADIUS 认证</td>
  </tr>
  <tr>
    <td>OpenID 认证（实现单点登录）</td>
  </tr>
  <tr>
    <td rowspan="2">MFA认证</td>
    <td>MFA 二次认证（Google Authenticator）</td>
  </tr>
  <tr>
    <td>RADIUS 二次认证</td>
  </tr>
  <tr>
    <td>登录复核（X-PACK）</td>
    <td>用户登录行为受管理员的监管与控制</td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td></td>
    <td></td>
    <td></td>
  </tr>
</table>

## 安装及使用指南

-  [Docker 快速安装文档](http://docs.jumpserver.org/zh/docs/dockerinstall.html)
-  [Step by Step 安装文档](http://docs.jumpserver.org/zh/docs/step_by_step.html)
-  [完整文档](http://docs.jumpserver.org)

## 演示视频和截屏

我们提供了演示视频和系统截图可以让你快速了解 Jumpserver：

- [演示视频](https://jumpserver.oss-cn-hangzhou.aliyuncs.com/jms-media/%E3%80%90%E6%BC%94%E7%A4%BA%E8%A7%86%E9%A2%91%E3%80%91Jumpserver%20%E5%A0%A1%E5%9E%92%E6%9C%BA%20V1.5.0%20%E6%BC%94%E7%A4%BA%E8%A7%86%E9%A2%91%20-%20final.mp4)
- [系统截图](http://docs.jumpserver.org/zh/docs/snapshot.html)

## SDK

我们编写了一些SDK，供您的其它系统快速和 Jumpserver API 交互：

- [Python](https://github.com/jumpserver/jumpserver-python-sdk) Jumpserver 其它组件使用这个 SDK 完成交互
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) 恺珺同学提供的 Java 版本的 SDK

## License & Copyright

Copyright (c) 2014-2019 飞致云 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
