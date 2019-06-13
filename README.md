## Jumpserver 多云环境下更好用的堡垒机

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.1-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Ansible](https://img.shields.io/badge/ansible-2.4.2.0-blue.svg?style=plastic)](https://www.ansible.com/)
[![Paramiko](https://img.shields.io/badge/paramiko-2.4.1-green.svg?style=plastic)](http://www.paramiko.org/)


----

Jumpserver 是全球首款完全开源的堡垒机，使用 GNU GPL v2.0 开源协议，是符合 4A 的专业运维审计系统。

Jumpserver 使用 Python / Django 进行开发，遵循 Web 2.0 规范，配备了业界领先的 Web Terminal 解决方案，交互界面美观、用户体验好。

Jumpserver 采纳分布式架构，支持多机房跨区域部署，中心节点提供 API，各机房部署登录节点，可横向扩展、无并发限制。

改变世界，从一点点开始。

- [English Version](https://github.com/jumpserver/jumpserver/blob/master/README_EN.md)


### 功能
----

<table class="subscription-level-table">
    <tr class="subscription-level-tr-border">
        <th  style="background-color: #1ab394;color: #ffffff;" colspan="3">Jumpserver提供的堡垒机必备功能</th>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="4">身份验证 Authentication</td>
        <td class="features-second-td-background-style" rowspan="3" >登录认证
        </td>
        <td class="features-third-td-background-style">资源统一登录和认证
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">LDAP认证
        </td>
    </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-third-td-background-style">支持OpenID，实现单点登录
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


### 开始使用
----

- 快速开始文档  [Docker 安装](http://docs.jumpserver.org/zh/docs/dockerinstall.html)

- Step by Step 安装文档 [详细部署](http://docs.jumpserver.org/zh/docs/step_by_step.html)

- 也可以查看我们完整文档 [文档](http://docs.jumpserver.org)

### Demo、视频 和 截图
----

我们提供了 Demo 、演示视频和截图可以让你快速了解 Jumpserver

- [Demo](https://demo.jumpserver.org/auth/login/?next=/)
- [视频](https://fit2cloud2-offline-installer.oss-cn-beijing.aliyuncs.com/tools/Jumpserver%20%E4%BB%8B%E7%BB%8Dv1.4.mp4)
- [截图](http://docs.jumpserver.org/zh/docs/snapshot.html)

### SDK
----

我们还编写了一些SDK，供你的其它系统快速和 Jumpserver API 交互

- [Python](https://github.com/jumpserver/jumpserver-python-sdk) Jumpserver其它组件使用这个SDK完成交互
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) 恺珺同学提供的Java版本的SDK


### License & Copyright
Copyright (c) 2014-2019 飞致云 FIT2CLOUD, All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
