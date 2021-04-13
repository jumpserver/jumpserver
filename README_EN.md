# Jumpserver - The Bastion Host for Multi-Cloud Environment

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-2.2-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Docker Pulls](https://img.shields.io/docker/pulls/jumpserver/jms_all.svg)](https://hub.docker.com/u/jumpserver)

- [中文版](https://github.com/jumpserver/jumpserver/blob/master/README.md)

|![notification](https://raw.githubusercontent.com/goharbor/website/master/docs/img/readme/bell-outline-badged.svg)Security Notice|
|------------------|
|On 15th January 2021, JumpServer found a critical bug for remote execution vulnerability. Please fix it asap! [For more detail](https://github.com/jumpserver/jumpserver/issues/5533) Thanks for **reactivity of Alibaba Hackerone bug bounty program** report use the bug|

--------------------------

Jumpserver is the world's first open-source Bastion Host and is licensed under the GNU GPL v2.0. It is a 4A-compliant professional operation and maintenance security audit system.

Jumpserver uses Python / Django for development, follows Web 2.0 specifications, and is equipped with an industry-leading Web Terminal solution that provides a beautiful user interface and great user experience

Jumpserver adopts a distributed architecture to support multi-branch deployment across multiple cross-regional areas. The central node provides APIs, and login nodes are deployed in each branch. It can be scaled horizontally without concurrency restrictions.

Change the world by taking every little step

----
### Advantages

- Open Source: huge transparency and free to access with quick installation process.
- Distributed: support large-scale concurrent access with ease.
- No Plugin required: all you need is a browser, the ultimate Web Terminal experience.
- Multi-Cloud supported: a unified system to manage assets on different clouds at the same time
- Cloud storage: audit records are stored in the cloud. Data lost no more!
- Multi-Tenant system: multiple subsidiary companies or departments access the same system simultaneously.
- Many applications supported: link to databases, windows remote applications, and Kubernetes cluster, etc.

## Features List

<table>
  <tr>
    <td rowspan="8">Authentication</td>
    <td rowspan="5">Login</td>
    <td>Unified way to access and authenticate resources</td>
  </tr>
  <tr>
    <td>LDAP/AD Authentication</td>
  </tr>
  <tr>
    <td>RADIUS Authentication</td>
  </tr>
  <tr>
    <td>OpenID Authentication（Single Sign-On）</td>
  </tr>
  <tr>
    <td>CAS Authentication （Single Sign-On）</td>
  </tr>
  <tr>
    <td rowspan="2">MFA (Multi-Factor Authentication)</td>
    <td>Use Google Authenticator for MFA</td>
  </tr>
  <tr>
    <td>RADIUS (Remote Authentication Dial In User Service)</td>
  </tr>
  <tr>
    <td>Login Supervision</td>
    <td>Any user’s login behavior is supervised and controlled by the administrator:small_orange_diamond:</td>
  </tr>
  <tr>
    <td rowspan="11">Accounting</td>
    <td rowspan="2">Centralized Accounts Management</td>
    <td>Admin Users management</td>
  </tr>
  <tr>
    <td>System Users management</td>
  </tr>
  <tr>
    <td rowspan="4">Unified Password Management</td>
    <td>Asset password custody (a matrix storing all asset password with dense security)</td>
  </tr>
  <tr>
    <td>Auto-generated passwords</td>
  </tr>
  <tr>
    <td>Automatic password handling (auto login assets)</td>
  </tr>
  <tr>
    <td>Password expiration settings</td>
  </tr>
  <tr>
    <td rowspan="2">Password change Schedular</td>
    <td>Support regular batch Linux/Windows assets password changing:small_orange_diamond:</td>
  </tr>
  <tr>
    <td>Implement multiple password strategies:small_orange_diamond:</td>
  </tr>
  <tr>
    <td>Multi-Cloud Management</td>
    <td>Automatically manage private cloud and public cloud assets in a unified platform :small_orange_diamond:</td>
  </tr>
  <tr>
    <td>Users Acquisition </td>
    <td>Create regular custom tasks to collect system users in selected assets to identify and track the privileges ownership:small_orange_diamond:</td>
  </tr>
  <tr>
    <td>Password Vault </td>
    <td>Unified operations to check, update, and test system user password to prevent stealing or unauthorised sharing of passwords:small_orange_diamond:</td>
  </tr>
  <tr>
    <td rowspan="15">Authorization</td>
    <td>Multi-Dimensional</td>
    <td>Granting users or user groups to access assets, asset nodes, or applications through system users. Providing precise access control to different roles of users</td>
  </tr>
  <tr>
    <td rowspan="4">Assets</td>
    <td>Assets are arranged and displayed in a tree structure </td>
  </tr>
  <tr>
    <td>Assets and Nodes have immense flexibility for authorizing</td>
  </tr>
  <tr>
    <td>Assets in nodes inherit authorization automatically</td>
  </tr>
  <tr>
    <td>child nodes automatically inherit authorization from parent nodes</td>
  </tr>
  <tr>
    <td rowspan="2">Application</td>
    <td>Provides granular access control for privileged users on application level to protect from unauthorized access and unintentional errors</td>
  </tr>
  <tr>
    <td>Database applications (MySQL, Oracle, PostgreSQL, MariaDB, etc.) and Remote App:small_orange_diamond: </td>
  </tr>
  <tr>
    <td>Actions</td>
    <td>Deeper restriction on the control of file upload, download and connection actions of authorized assets. Control the permission of clipboard copy/paste (from outer terminal to current asset)</td>
  </tr>
  <tr>
    <td>Time Bound</td>
    <td>Sharply limited the available (accessible) time for account access to the authorized resources to reduce the risk and attack surface drastically</td>
  </tr>
  <tr>
    <td>Privileged Assignment</td>
    <td>Assign the denied/allowed command lists to different system users as privilege elevation, with the latter taking the form of allowing particular commands to be run with a higher level of privileges. (Minimize insider threat)</td>
  </tr>
  <tr>
    <td>Command Filtering</td>
    <td>Creating list of restriction commands that you would like to assign to different authorized system users for filtering purpose</td>
  </tr>
  <tr>
    <td>File Transfer and Management</td>
    <td>Support SFTP file upload/download</td>
  </tr>
  <tr>
    <td>File Management</td>
    <td>Provide a Web UI for SFTP file management</td>
  </tr>
  <tr>
    <td>Workflow Management</td>
    <td>Manage user login confirmation requests and assets or applications authorization requests for Just-In-Time Privileges functionality:small_orange_diamond:</td>
  </tr>
  <tr>
    <td>Group Management </td>
    <td>Establishing a multi-tenant ecosystem that able authority isolation to keep malicious actors away from sensitive administrative backends:small_orange_diamond:</td>
  </tr>
  <tr>
    <td rowspan="8">Auditing</td>
    <td>Operations</td>
    <td>Auditing user operation behaviors for any access or usage of given privileged accounts</td>
  </tr>
  <tr>
    <td rowspan="2">Session</td>
    <td>Support real-time session audit</td>
  </tr>
  <tr>
    <td>Full history of all previous session audits</td>
  </tr>
  <tr>
    <td rowspan="3">Video</td>
    <td>Complete session audit and playback recordings on assets operation (Linux, Windows)</td>
  </tr>
  <tr>
    <td>Full recordings of RemoteApp, MySQL, and Kubernetes:small_orange_diamond:</td>
  </tr>
  <tr>
    <td>Supports uploading recordings to public clouds</td>
  </tr>
  <tr>
    <td>Command</td>
    <td>Command auditing on assets and applications operation. Send warning alerts when executing illegal commands</td>
  </tr>
  <tr>
    <td>File Transfer</td>
    <td>Full recordings of file upload and download</td>
  </tr>
  <tr>
    <td rowspan="20">Database</td>
    <td rowspan="2">How to connect</td>
    <td>Command line</td>
  </tr>
  <tr>
    <td>Built-in Web UI:small_orange_diamond:</td>
  </tr>

  <tr>
    <td rowspan="4">Supported Database</td>
    <td>MySQL</td>
  </tr>
  <tr>
    <td>Oracle :small_orange_diamond:</td>
  </tr>
  <tr>
    <td>MariaDB :small_orange_diamond:</td>
  </tr>
  <tr>
    <td>PostgreSQL :small_orange_diamond:</td>
  </tr>
  <tr>
    <td rowspan="6">Feature Highlights</td>
    <td>Syntax highlights</td>
  </tr>
  <tr>
    <td>Prettier SQL formmating</td>
  </tr>
  <tr>
    <td>Support Shortcuts</td>
  </tr>
  <tr>
    <td>Support selected SQL statements</td>
  </tr>
  <tr>
    <td>SQL commands history query</td>
  </tr>
  <tr>
    <td>Support page creation: DB, TABLE</td>
  </tr>
  <tr>
    <td rowspan="2">Session Auditing</td>
    <td>Full records of command</td>
  </tr>
  <tr>
    <td>Playback videos</td>
  </tr>
</table>

**Note**: Rows with :small_orange_diamond: at the end of the sentence means that it is X-PACK features exclusive ([Apply for X-PACK Trial](https://jinshuju.net/f/kyOYpi))

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
- [Java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) Thanks to 恺珺 for providing his Java SDK vesrion.

## JumpServer Component Projects
- [Lina](https://github.com/jumpserver/lina) JumpServer Web UI
- [Luna](https://github.com/jumpserver/luna) JumpServer Web Terminal
- [KoKo](https://github.com/jumpserver/koko) JumpServer Character protocaol Connector, replace original Python Version [Coco](https://github.com/jumpserver/coco)
- [Guacamole](https://github.com/jumpserver/docker-guacamole) JumpServer Graphics protocol Connector，rely on [Apache Guacamole](https://guacamole.apache.org/)

## Contribution
If you have any good ideas or helping us to fix bugs, please submit a Pull Request and accept our thanks :)

Thanks to the following contributors for making JumpServer better everyday!

<a href="https://github.com/jumpserver/jumpserver/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=jumpserver/jumpserver" />
</a>


## Thanks to
- [Apache Guacamole](https://guacamole.apache.org/) Web page connection RDP, SSH, VNC protocol equipment. JumpServer graphical connection dependent.
- [OmniDB](https://omnidb.org/) Web page connection to databases. JumpServer Web database dependent.


## JumpServer Enterprise Version 
- [Apply for it](https://jinshuju.net/f/kyOYpi)

## Case Study

- [JumpServer 堡垒机护航顺丰科技超大规模资产安全运维](https://blog.fit2cloud.com/?p=1147)；
- [JumpServer 堡垒机让“大智慧”的混合 IT 运维更智慧](https://blog.fit2cloud.com/?p=882)；
- [携程 JumpServer 堡垒机部署与运营实战](https://blog.fit2cloud.com/?p=851)；
- [小红书的JumpServer堡垒机大规模资产跨版本迁移之路](https://blog.fit2cloud.com/?p=516)；
- [JumpServer堡垒机助力中手游提升多云环境下安全运维能力](https://blog.fit2cloud.com/?p=732)；
- [中通快递：JumpServer主机安全运维实践](https://blog.fit2cloud.com/?p=708)；
- [东方明珠：JumpServer高效管控异构化、分布式云端资产](https://blog.fit2cloud.com/?p=687)；
- [江苏农信：JumpServer堡垒机助力行业云安全运维](https://blog.fit2cloud.com/?p=666)。

## For safety instructions

JumpServer is a security product. Please refer to [Basic Security Recommendations](https://docs.jumpserver.org/zh/master/install/install_security/) for deployment and installation.

If you find a security problem, please contact us directly：

- ibuler@fit2cloud.com 
- support@fit2cloud.com 
- 400-052-0755

### License & Copyright
Copyright (c) 2014-2019 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
