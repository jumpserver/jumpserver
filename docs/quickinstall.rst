快速安装
++++++++++++++++++++++++

因为懒，所以更专业。

组件解释
~~~~~~~~~~~~~~
- Jumpserver 为管理后台，管理员可以通过Web页面进行资产管理、用户管理、资产授权等操作
- Coco 为 SSH Server 和 Web Terminal Server 。用户可以通过使用自己的账户登录 SSH 或者 Web Terminal 直接访问被授权资产。不需要知道服务器的账户密码
- Luna 为 Web Terminal Server 前端页面，用户使用 Web Terminal 方式登录所需要的组件
- Guacamole 为 Windows 组件，用户可以通过 Web Terminal 来连接 Windows 资产 （暂时只能通过 Web Terminal 来访问）

安装文档
~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   setup_by_centos7.rst
