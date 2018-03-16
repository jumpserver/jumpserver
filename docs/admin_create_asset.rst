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