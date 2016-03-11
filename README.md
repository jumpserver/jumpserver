## 写在前面
 - 目前本版本处于beta阶段，请不要用于生产环境，除非你知道你在做什么
 - 本版本暂时没加入LDAP接口，稳定版会将LDAP和无Agent方式抽象成API，2.x版本支持LDAP，请移步release中下载

#欢迎使用Jumpserver
**Jumpserver** 是一款由python编写开源的跳板机(堡垒机)系统，实现了跳板机应有的功能。基于ssh协议来管理，客户端无需安装agent。
支持常见系统:
 1. redhat centos
 2. debian
 3. suse ubuntu
 4. freebsd
 5. 其他ssh协议硬件设备

###截图：

首页
 
![webterminal](https://github.com/ibuler/static/raw/master/jumpserver3/index.jpg)

WebTerminal:

![webterminal](https://github.com/ibuler/static/raw/master/jumpserver3/webTerminal.gif)

Web批量执行命令

![WebExecCommand](https://github.com/ibuler/static/raw/master/jumpserver3/webExec.gif)

录像回放

![录像](https://github.com/ibuler/static/raw/master/jumpserver3/record.gif)

跳转和批量命令

![跳转](https://github.com/ibuler/static/raw/master/jumpserver3/connect.gif)

命令统计

![跳转](https://github.com/ibuler/static/raw/master/jumpserver3/command.jpg)

### 文档

* [访问wiki](https://github.com/jumpserver/jumpserver/wiki)
* [概览](https://github.com/jumpserver/jumpserver/wiki/%E6%A6%82%E8%A7%88)
* [名词解释](https://github.com/jumpserver/jumpserver/wiki/%E5%90%8D%E8%AF%8D%E8%A7%A3%E9%87%8A)
* [常见问题](https://github.com/jumpserver/jumpserver/wiki/%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)
* 安装基于：[RedHat 的系统](https://github.com/jumpserver/jumpserver/wiki/%E5%9F%BA%E4%BA%8E-RedHat-%E7%9A%84%E7%B3%BB%E7%BB%9F)，[Debian 的系统](https://github.com/jumpserver/jumpserver/wiki/%E5%9F%BA%E4%BA%8E-Debian-%E7%9A%84%E7%B3%BB%E7%BB%9F)
* [快速开始](https://github.com/jumpserver/jumpserver/wiki/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)

### 特点

* 完全开源，GPL授权
* Python编写，容易再次开发
* 实现了跳板机基本功能，认证、授权、审计
* 集成了Ansible，批量命令等
* 支持WebTerminal
* Bootstrap编写，界面美观
* 自动收集硬件信息
* 录像回放
* 命令搜索
* 实时监控
* 批量上传下载

### 其它

[Jumpserver官网](http://www.jumpserver.org)

[论坛](http://bbs.jumpserver.org)

[demo站点](http://demo.jumpserver.org)

交流群: 399218702

### 团队

![](https://github.com/ibuler/static/raw/master/jumpserver3/team.jpg)




