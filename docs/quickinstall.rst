进阶安装
++++++++++++++++++++++++
可用于生产环境参考安装文档

组件说明
~~~~~~~~~~~~~~
- Jumpserver 为管理后台，管理员可以通过Web页面进行资产管理、用户管理、资产授权等操作
- Coco 为 SSH Server 和 Web Terminal Server 。用户可以通过使用自己的账户登录 SSH 或者 Web Terminal 直接访问被授权的资产。不需要知道服务器的账户密码
- Luna 为 Web Terminal Server 前端页面，用户使用 Web Terminal 方式登录所需要的组件
- Guacamole 为 Windows 组件，用户可以通过 Web Terminal 来连接 Windows 资产 （暂时只能通过 Web Terminal 来访问）

端口说明
~~~~~~~~~~~~~~
- Jumpserver 默认端口为 8080/tcp 配置文件在 jumpserver/config.py
- Coco 默认 SSH 端口为 2222/tcp ，默认 Web Terminal 端口为 5000/tcp 配置文件在 coco/conf.py
- Guacamole 默认端口为 8081/tcp 在 docker run 时指定
- Nginx 默认端口为 80/tcp 配置在 nginx/nginx.conf 中指定

一体化部署文档（基于CentOS 7）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   安装文档 <setup_by_centos7.rst>

分布式部署文档（基于CentOS 7）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   环境说明 <distributed_01.rst>
   nginx 代理部署 <distributed_02.rst>
   数据库 部署 <distributed_03.rst>
   jumpserver 部署 <distributed_04.rst>
   coco 部署 <distributed_05.rst>
   guacamole 部署 <distributed_06.rst>
