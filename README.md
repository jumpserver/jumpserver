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

<table class="subscription-level-table">
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="4">身份验证 Authentication</td>
        <td class="features-second-td-background-style" rowspan="3" >登录认证
        </td>
        <td class="features-third-td-background-style">资源统一登录和认证
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">LDAP 认证
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">支持 OpenID，实现单点登录
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">多因子认证
        </td>
        <td class="features-third-td-background-style">MFA（Google Authenticator）
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="9">账号管理 Account</td>
        <td class="features-second-td-background-style" rowspan="2">集中账号管理
        </td>
        <td class="features-third-td-background-style">管理用户管理
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">系统用户管理
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style" rowspan="4">统一密码管理
        </td>
        <td class="features-third-td-background-style">资产密码托管
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">自动生成密码
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">密码自动推送
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">密码过期设置
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style" rowspan="2">批量密码变更(X-PACK)
        </td>
        <td class="features-outline-td-background-style">定期批量修改密码
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">生成随机密码
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">多云环境的资产纳管(X-PACK)
        </td>
        <td class="features-outline-td-background-style">对私有云、公有云资产统一纳管
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="9">授权控制 Authorization</td>
        <td class="features-second-td-background-style" rowspan="3">资产授权管理
        </td>
        <td class="features-third-td-background-style">资产树
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">资产或资产组灵活授权
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">节点内资产自动继承授权
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">RemoteApp(X-PACK)
        </td>
        <td class="features-outline-td-background-style">实现更细粒度的应用级授权
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-outline-td-background-style">组织管理(X-PACK)
        </td>
        <td class="features-outline-td-background-style">实现多租户管理，权限隔离
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">多维度授权
        </td>
        <td class="features-third-td-background-style">可对用户、用户组或系统角色授权
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">指令限制
        </td>
        <td class="features-third-td-background-style">限制特权指令使用，支持黑白名单
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">统一文件传输
        </td>
        <td class="features-third-td-background-style">SFTP 文件上传/下载
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">文件管理
        </td>
        <td class="features-third-td-background-style">Web SFTP 文件管理
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="6">安全审计 Audit</td>
        <td class="features-second-td-background-style" rowspan="2">会话管理
        </td>
        <td class="features-third-td-background-style">在线会话管理
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">历史会话管理
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style" rowspan="2">录像管理
        </td>
        <td class="features-third-td-background-style">Linux 录像支持
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">Windows 录像支持
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">指令审计
        </td>
        <td class="features-third-td-background-style">指令记录
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">文件传输审计
        </td>
        <td class="features-third-td-background-style">上传/下载记录审计
        </td>
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
