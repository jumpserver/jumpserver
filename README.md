## Jumpserver

[![Python3](https://img.shields.io/badge/python-3.6-green.svg?style=plastic)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-1.11-brightgreen.svg?style=plastic)](https://www.djangoproject.com/)
[![Ansible](https://img.shields.io/badge/ansible-2.2.2.0-blue.svg?style=plastic)](https://www.ansible.com/)
[![Paramiko](https://img.shields.io/badge/paramiko-2.1.2-green.svg?style=plastic)](http://www.paramiko.org/)

Jumpserver is a open source proxy server, developed by `Python` and `Django`, aim to help 
companies to efficiently user, assets, authority and audit management

Jumpserver是一款使用Python, Django开发的开源跳板机系统, 助力互联网企业高效 用户、资产、权限、审计 管理

### Feature 功能
  - Auth 统一认证
  - CMDB 资产管理
  - Perm 统一授权
  - Audit 审计
  - LDAP AUTH 支持LDAP认证
  - Web terminal
  - SSH Server


### Environment 环境
   * Python 3.6  
   * Django 1.11

### Install 安装 
Using docker compose to setup it

使用docker compose 安装，一键完成，docker compose 安装见 docker官方

   $ docker-compose up

### Usage 使用
   1. Visit http://$HOST:8080 (访问 http://你的主机IP:8080 来访问 Jumpserver)
 
   2. Click left navigation visit Applications-Terminal and accept coco and luna register
      (点击左侧 应用程序接受 Coco和Luna的注册)
   
   3. Click Assets-Admin user, Create admin user
      (添加 管理用户)
   
   4. Click Assets-System user, Create system user
      (添加 系统用户)
      
   5. Click Assets-Asset, Add a asset
      (添加 资产)
   
   6. Click Perms-Asset permission, Add a perm rule
      (添加授权规则，授权给admin)
   
   7. Connect ssh server coco (连接 ssh server coco)
      
      ssh -p2222 $USER@$Host
 
   8. Visit web terminal server Luna, click server test connection
      (访问 访问Luna，点击左侧服务器连接测试)
      
      http://$HOST:5000
   
   
### Snapshot 截图

    https://github.com/jumpserver/jumpserver/issues/438


### Demo

demo使用了开发者模式，并发只能为1 

- Jumpserver: [访问](http://demo.jumpserver.org:8080)  账号: admin 密码: admin

- Luna: [访问](http://demo.jumpserver.org:5000) 同Jumpserver认证

- Coco: ssh -p 2222 admin@demo.jumpserver.org 密码: admin

### ROADMAP

参见 https://github.com/jumpserver/jumpserver/milestone/2

### Docs 开发者文档


   * [Project structure 项目结构描述](https://github.com/jumpserver/jumpserver/blob/dev/docs/project_structure.md)
   * [Code style Python代码规范](https://github.com/jumpserver/jumpserver/blob/dev/docs/python_style_guide.md)
   * [Api style API设计规范](https://github.com/jumpserver/jumpserver/blob/dev/docs/api_style_guide.md)

### Contributor 贡献者
#### 0.4.0
- ibuler <广宏伟>
- 小彧 <李磊> Django资深开发者，为users模块贡献了很多代码
- sofia <周小侠> 资深前端工程师, luna前端代码贡献者和现在维护者
- liuz <刘正> 全栈工程师, 编写了luna大部分代码
- jiaxiangkong <陈尚委> Jumpserver测试运营

#### 0.3.2 
- halcyon <王墉> DevOps 资深开发者, 0.3.2 核心开发者之一
- yumaojun03 <喻茂峻> DevOps 资深开发者，jperm开发者，擅长Python, Go以及PAAS平台开发
- kelianchun <柯连春> DevOps 资产开发者，fix了很多connect.py bug

### 开发者群
如果你为Jumpserver贡献过代码，请加一下群 （需要验证一下你的github id）

群号: 489385245

### License & Copyright
Copyright (c) 2014-2017 Beijing Duizhan Tech, Inc., All rights reserved.

Licensed under The GNU General Public License version 2 (GPLv2)  (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

https://www.gnu.org/licenses/gpl-2.0.html

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
