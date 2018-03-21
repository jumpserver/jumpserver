个人资产
=========

这里介绍用户个人资产相关的功能。

.. contents:: Topics

.. _view_personal_assets:

查看个人资产
````````````

创建授权规则的时候，选择了用户组，所以这里需要登录所选用户组下面的用户才能看见相应的资产。

.. image:: _static/img/jumpserver_user_list.jpg

用户正确登录后的页面：

.. image:: _static/img/user_login_success.jpg

.. _host_login:

主机登录
`````````

点击页面左边的 Web 终端：

.. image:: _static/img/link_web_terminal.jpg

打开资产所在的节点：

.. image:: _static/img/luna_index.jpg

双击资产名字，就连上资产了：

如果显示连接超时，请检查为资产分配的系统用户用户名和密钥是否正确，是否正确选择 Windows 操作系统，协议 rdp，端口3389，是否正确选择 Linux 操作系统，协议 ssh，端口22，以及资产的防火墙策略是否正确配置等信息。

.. image:: _static/img/windows_assert.jpg

接下来，就可以对资产进行操作了。

.. _host_logout:

主机登出
`````````

点击页面顶部的 Server 按钮会弹出选个选项，第一个断开所选的连接，第二个断开所有连接：

.. image:: _static/img/disconnect_assert.jpg