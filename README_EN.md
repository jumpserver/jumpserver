## Jumpserver 

![Total visitor](https://visitor-count-badge.herokuapp.com/total.svg?repo_id=jumpserver)
![Visitors in today](https://visitor-count-badge.herokuapp.com/today.svg?repo_id=jumpserver)
[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.1-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Ansible](https://img.shields.io/badge/ansible-2.4.2.0-blue.svg?style=plastic)](https://www.ansible.com/)
[![Paramiko](https://img.shields.io/badge/paramiko-2.4.1-green.svg?style=plastic)](http://www.paramiko.org/)


----

- [中文版](https://github.com/jumpserver/jumpserver/blob/master/README_EN.md)

Jumpserver is the first fully open source bastion in the world, based on the GNU GPL v2.0 open source protocol. Jumpserver is a  professional operation and maintenance audit system conforms to 4A specifications.

Jumpserver is developed using Python / Django, conforms to the Web 2.0 specification, and is equipped with the industry-leading Web Terminal solution which have beautiful interface and great user experience.

Jumpserver adopts a distributed architecture to support multi-branch deployment across multiple areas. The central node provides APIs, and login nodes are deployed in each branch. It can be scaled horizontally without concurrency restrictions.

Change the world, starting from little things.

----

### Features


<table class="subscription-level-table">
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="5" style="text-align: center">
            身份验证
            <br>
            <span>Authentication</span>
        </td>
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
        <td class="features-second-td-background-style">登录复核
        </td>
        <td class="features-third-td-background-style">支持二次登录复核
        </td>
      </tr>
    <tr class="subscription-level-tr-border">
        <td class="features-first-td-background-style" rowspan="9" style="text-align: center" >
            账号管理
            <br>
            <span>Account</span>
        </td>
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
        <td class="features-first-td-background-style" rowspan="10" style="text-align: center">
            授权控制
            <br>
            <span>Authorization</span>
        </td>
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
        <td class="features-outline-td-background-style">数据库授权
        </td>
        <td class="features-outline-td-background-style">实现mysql数据库应用级授权
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
        <td class="features-first-td-background-style" rowspan="7" style="text-align: center">
            安全审计
            <br>
            <span>Audit</span>
        </td>
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
    <tr class="subscription-level-tr-border">
        <td class="features-second-td-background-style">工单管理
        </td>
        <td class="features-third-td-background-style">二次登录复核管理
        </td>
     </tr>
</table>


### Start 

Quick start  [Docker Install](http://docs.jumpserver.org/zh/docs/dockerinstall.html)

Step by Step deployment. [Docs](http://docs.jumpserver.org/zh/docs/step_by_step.html)

Full documentation [Docs](http://docs.jumpserver.org)

### Demo、Video 和 Snapshot

We provide online demo, demo video and screenshots to get you started quickly.

[Demo](https://demo.jumpserver.org/auth/login/?next=/)
[Video](https://fit2cloud2-offline-installer.oss-cn-beijing.aliyuncs.com/tools/Jumpserver%20%E4%BB%8B%E7%BB%8Dv1.4.mp4)
[Snapshot](http://docs.jumpserver.org/zh/docs/snapshot.html)

### SDK

We provide the SDK for your other systems to quickly interact with the Jumpserver API.

- [Python](https://github.com/jumpserver/jumpserver-python-sdk) Jumpserver other components use this SDK to complete the interaction.
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) 恺珺同学提供的Java版本的SDK thanks to 恺珺 for provide Java SDK


### License & Copyright
Copyright (c) 2014-2019 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
