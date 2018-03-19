快速入门
==================

必备条件
````````````````

- 一台安装好 Jumpserver 系统的可用主机（堡垒机）
- 一台或多台可用的 Linux、Windows资产设备（被管理的资产）

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

鉴于，心态检测存在延迟，您也可以直接在 Jumpserver 主机上执行如下命令检测 Coco 是否存活，Coco 服务默认使用 2222 端口:

::

    $ netstat -ntpl

效果如下：

.. image:: _static/img/coco_check_terminal.jpg

命令行登录 Jumpserver 使用如下命令：

::

    $ ssh -p 2222 用户名@Jumpserver IP地址

登录成功后界面如下:

.. image:: _static/img/coco_success.jpg

三、创建资产
``````````````````

3.1 创建 Linux 资产

3.1.1 编辑资产树

节点不能重名，右击节点可以添加、删除和重命名节点，以及进行资产相关的操作。

.. image:: _static/img/asset_tree.jpg

3.1.2 创建管理用户

管理用户是服务器的 root，或拥有 NOPASSWD: ALL sudo 权限的用户，Jumpserver 使用该用户来 `推送系统用户`、`获取资产硬件信息`等。

名称可以按资产树来命名。用户名root。密码和 SSH 私钥必填一个。

.. image:: _static/img/create_asset_admin_user.jpg

3.1.3 创建系统用户

系统用户是 Jumpserver 跳转登录资产时使用的用户，可以理解为登录资产用户，如 web, sa, dba(`ssh web@some-host`), 而不是使用某个用户的用户名跳转登录服务器(`ssh xiaoming@some-host`); 简单来说是 用户使用自己的用户名登录Jumpserver, Jumpserver使用系统用户登录资产。

系统用户创建时，如果选择了自动推送 Jumpserver 会使用 Ansible 自动推送系统用户到资产中，如果资产(交换机、Windows )不支持 Ansible, 请手动填写账号密码。

Linux 系统协议项务必选择 ssh 。如果用户在系统中已存在，请去掉自动生成密钥、自动推送勾选。

.. image:: _static/img/create_asset_system_user.jpg

3.1.4 创建资产

点击页面左侧的“资产管理”菜单下的“资产列表”按钮，查看当前所有的资产列表。

点击页面左上角的“创建资产”按钮，进入资产创建页面，填写资产信息。

IP 地址和管理用户要确保正确，确保所选的管理用户的用户名和密码能"牢靠"地登录指定的主机 IP 上。资产的系统平台也务必正确填写。公网 IP 只用于展示信息，可不填，Jumpserver 连接资产主机使用的是 IP 地址。

.. image:: _static/img/create_asset.jpg

资产创建信息填写好保存之后，可测试资产是否能正确连接。

.. image:: _static/img/check_asset_connect.jpg

如果资产不能连接，请检查管理用户的用户名和密钥是否正确以及该管理用户能使用 SSH 从 Jumpserver 主机正确登录到资产主机上。

3.2 创建 Windows 资产

3.2.1 创建 Windows 系统管理用户

同 Linux 系统的管理用户一样，名称可以按资产树来命名，用户名是管理员用户名，密码是管理员的密码。

.. image:: _static/img/create_windows_admin.jpg

3.2.2 创建 Windows 系统系统用户

由于目前 Windows 不支持自动推送，所以 Windows 的系统用户设置成与管理用户同一个用户。

Windows 资产协议务必选择 rdp。

.. image:: _static/img/create_windows_user.jpg

3.2.3 创建 Windows 资产

同创建 Linux 资产一样。

创建 Windows 资产，系统平台请选择正确的 Windows，端口号为3389，IP 和 管理用户请选择正确，确保管理用户能正确登录到指定 IP 的主机上。

.. image:: _static/img/create_windows_asset.jpg

