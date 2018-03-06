组件说明
=================

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


架构图

.. image:: _static/img/structure.png
    :alt: 组件架构图