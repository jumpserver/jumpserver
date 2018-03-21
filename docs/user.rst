用户列表
========

这里介绍用户列表的功能。

点击页面左侧“用户列表”菜单下的“用户列表“，进入用户列表页面。

.. contents:: Topics

.. _create_user:

创建用户
````````

点击页面左侧“用户列表”菜单下的“用户列表“，进入用户列表页面。

点击页面左上角“创建用户”按钮，进入创建用户页面，填写账户，角色安全，个人等信息。

其中，用户名即 Jumpserver 登录账号。用户组是用于资产授权，当某个资产对一个用户组授权后，这个用户组下面的所有用户就都可以使用这个资产了。角色用于区分一个用户是管理员还是普通用户。

.. image:: _static/img/create_jumpserver_user.jpg

成功提交用户信息后，Jumpserver 会发送一条设置"用户密码"的邮件到您填写的用户邮箱。

.. image:: _static/img/create_user_success.jpg

点击邮件中的设置密码链接，设置好密码后，您就可以用户名和密码登录 Jumpserver 了。

用户首次登录 Junmpserver，会被要求完善用户信息。基本信息可以不变，但 SSH 密钥信息必须填上。

Linux/Unix 生成 SSH 密钥可以参考（https://www.cnblogs.com/horanly/p/6604104.html)

Windows 生成 SSH 密钥可以参考（https://www.cnblogs.com/horanly/p/6604104.html)

查看公钥信息：

::

    $ cat ~/.ssh/id_rsa.pub
    ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDadDXxxx......

复制 SSH 公钥，添加到 Jumpserver 中。

.. image:: _static/img/set_ssh_key.jpg


除了使用浏览器登录 Jumpserver 外，还可使用命令行登录：

确保 Coco 服务正常

.. image:: _static/img/coco_check.jpg

鉴于心态检测存在延迟，您也可以直接在 Jumpserver 主机上执行如下命令检测 Coco 是否存活，Coco 服务默认使用 2222 端口:

::

    $ netstat -ntpl

效果如下：

.. image:: _static/img/coco_check_terminal.jpg

命令行登录 Jumpserver 使用如下命令：

::

    $ ssh -p 2222 用户名@Jumpserver IP地址

登录成功后界面如下:

.. image:: _static/img/coco_success.jpg

.. _update_user:

更新用户
````````

点击页面右边的“更新”按钮，进入编辑用户页面，编辑用户信息，点击“提交”按钮，更新用户完成。

.. _delete_user:

删除用户
````````

点击页面右边的“删除”按钮，弹出是否删除确认框，点击“确定”按钮，删除用户完成。

.. _export_user:

导出用户
````````

选中用户，点击右上角的“导出”按钮，导出用户完成。

.. _import_user:

导入用户
````````

点击右上角的“导入”按钮，弹出导入对话框，选择要导入的CSV格式文件，点击“确认”按钮，导入用户完成。

.. _batch_user_operation:

批量操作
````````

选中用户，选择页面左下角的批量操作选项，点击”提交“按钮，批量操作完成。