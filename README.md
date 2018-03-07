## Jumpserver

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-1.11-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Ansible](https://img.shields.io/badge/ansible-2.2.2.0-blue.svg?style=plastic)](https://www.ansible.com/)
[![Paramiko](https://img.shields.io/badge/paramiko-2.1.2-green.svg?style=plastic)](http://www.paramiko.org/)


----

Jumpserver是全球首款完全开源的堡垒机，使用GNU GPL v2.0开源协议，是符合 4A 的专业运维审计系统。

Jumpserver使用Python / Django 进行开发，遵循 Web 2.0 规范，配备了业界领先的 Web Terminal 解决方案，交互界面美观、用户体验好。

Jumpserver采纳分布式架构，支持多机房跨区域部署，中心节点提供 API，各机房部署登录节点，可横向扩展、无并发访问限制。

改变世界，从一点点开始。

----

### 功能
  - 统一认证
  - 资产管理
  - 统一授权
  - 审计
  - 支持LDAP认证
  - Web terminal
  - SSH Server
  - 支持Windows RDP

### 开始使用

快速开始文档  [Docker安装](http://docs.jumpserver.org/zh/latest/quickstart.html)

一步一步安装文档 [详细部署](http://docs.jumpserver.org/zh/latest/step_by_step.html)

也可以查看我们完整文档包括了使用和开发 [文档](http://docs.jumpserver.org)

### Demo 和 截图 

我们提供了DEMO和截图可以让你快速了解Jumpserver

[DEMO](http://demo.jumpserver.org)
[截图](http://docs.jumpserver.org/zh/docs/snapshot.html)

### SDK 

我们还编写了一些SDK，供你其它系统快速和Jumpserver APi交互，

- [python](https://github.com/jumpserver/jumpserver-python-sdk) Jumpserver其它组件使用这个SDK完成交互
- [java](https://github.com/KaiJunYan/jumpserver-java-sdk.git) 恺珺同学提供的Java版本的SDK


### License & Copyright
Copyright (c) 2014-2017 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
