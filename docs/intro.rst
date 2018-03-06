简介
============

Jumpserver是混合云下更好用的堡垒机, 分布式架构设计无限扩展，轻松对接混合云资产，支持使用云存储（AWS S3, ES等）存储录像、命令

Jumpserver颠覆传统堡垒机, 无主机和并发数量限制，支持水平扩容，FIT2CLOUD提供完备的商业服务支持，用户无后顾之忧

Jumpserver拥有极致的用户体验, 极致UI体验，容器化的部署方式，部署过程方便快捷，可持续升级


组件说明
++++++++++++++++++++++++

Jumpserver
```````````
现指Jumpserver管理后台，是核心组件(Core), 使用 Django Class Based View 风格开发，支持Restful API。

`Github <https://github.com/jumpserver/jumpserver.git>`_


Coco
````````
实现了SSH Server 和 Web Terminal Server的组件，提供ssh和websocket接口, 使用 Paramiko 和 Flask 开发。


`Github <https://github.com/jumpserver/coco.git>`__


Luna
````````
现在是Web Terminal前端，计划前端页面都由该项目提供，Jumpserver只提供API，不再负责后台渲染html等。

`Github <https://github.com/jumpserver/luna.git>`__


Guacamole
```````````
Apache 跳板机项目，Jumpserver使用其组件实现RDP功能，Jumpserver并没有修改其代码而是添加了额外的插件，支持Jumpserver调用


Jumpserver-python-sdk
```````````````````````
Jumpserver API Python SDK，Coco目前使用该SDK与Jumpserver API交互

`Github <https://github.com/jumpserver/jumpserver-python-sdk.git>`__


组件架构图
++++++++++++++++++++++++
.. image:: _static/img/structure.png
    :alt: 组件架构图
