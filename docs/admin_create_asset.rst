创建资产
==================

必备条件
````````````````

- 一台安装好 Jumpserver 系统的可用主机（堡垒机）
- 一台或多台可用的资产设备（被管理的资产）

一、系统设置
````````````````````

1.1 基本设置

.. image:: _static/img/basic_setting.jpg

1.2 配置邮件发送服务器

.. image:: _static/img/smtp_setting.jpg

配置 QQ 邮箱的 SMTP 服务可参考（http://blog.csdn.net/Aaron133/article/details/78363844）

配置邮件服务后，点击页面的"测试连接"按钮，如果配置正确，Jumpserver 会发送一条测试邮件到您的 SMTP 账号邮箱里面。

.. image:: _static/img/smtp_test.jpg

二、创建用户
`````````````````````

2.1 创建 Jumpserver 用户

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

查看公钥信息

::

    $ cat ~/.ssh/id_rsa.pub
    ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDadDXxxx......

复制 SSH 公钥，添加到 Jumpserver 中。

.. image:: _static/img/set_ssh_key.jpg


除了使用浏览器登录 Jumpserver 外，还可使用命令行登录：

确保 Coco 服务正常

.. image:: _static/img/coco_check.jpg

使用如下命令：

::

    $ ssh -p 2222 用户名@Jumpserver IP地址

登录成功后界面如下:

.. image:: _static/img/coco_success.jpg

