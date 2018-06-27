快速入门
==================

必备条件
````````````````

- 一台安装好 Jumpserver 系统的可用主机（堡垒机）
- 一台或多台可用的 Linux、Windows资产设备（被管理的资产）

一、系统设置
````````````````````

1.1 基本设置

::

    # 修改 URL 的 localhost 为你的实际 url 地址，否则邮件收到的地址将为 localhost
    修改完 url 地址后需要重启 jumpserver 服务（重启才能生效，后续会解决这个问题）

.. image:: _static/img/basic_setting.jpg

1.2 邮件设置

::

    # 点击页面上边的"邮件设置" TAB ，进入邮件设置页面
    # 配置邮件服务后，点击页面的"测试连接"按钮，如果配置正确，Jumpserver 会发送一条测试邮件到
    您的 SMTP 账号邮箱里面，确定收到测试邮件后点击保存即可使用。

.. image:: _static/img/smtp_setting.jpg

1.3 LDAP设置

::

    # 先测试通过才能保存
    # DN 和 OU 一定要完整(如DN:cn=Manage,ou=Jumpserver,dc=jumpserver,ou=org)
    注：可借用第三方 gui 工具查看 ldap 用户的属性，新版本已经支持中文名登录，即cn=中文也可正常使用

1.4 终端设置

::

    # 命令记录保存到 elastic
    {"default": {"TYPE":"server"}, "ali-es": {"TYPE": "elasticsearch", "HOSTS": ["http://elastic:changeme@localhost:9200"]}}

    # 录像存储在 oss，Jumpserver 系统设置-终端设置 录像存储
    {"default": {"TYPE": "server"}, "cn-north-1": {"TYPE": "s3", "BUCKET": "jumpserver", "ACCESS_KEY": "", "SECRET_KEY": "", "REGION": "cn-north-1"}, "ali-oss": {"TYPE": "oss", "BUCKET": "jumpserver", "ACCESS_KEY": "", "SECRET_KEY": "", "ENDPOINT": "http://oss-cn-hangzhou.aliyuncs.com"}}

    注：修改后，需要修改在Jumpserver 会话管理-终端管理 修改terminal的配置 录像存储 命令记录，然后重启 Jumpserver 服务

1.5 安全设置

二、创建用户
`````````````````````

2.1 创建 Jumpserver 用户

::

    # 点击页面左侧“用户列表”菜单下的“用户列表“，进入用户列表页面
    # 点击页面左上角“创建用户”按钮，进入创建用户页面，（也可以通过右上角导入模版进行用户导入）
    # 其中，用户名即 Jumpserver 登录账号（具有唯一性，不能重名）。名称为页面右上角用户标识（可重复）
    # 成功提交用户信息后，Jumpserver 会发送一条设置"用户密码"的邮件到您填写的用户邮箱
    # 点击邮件中的设置密码链接，设置好密码后，您就可以用户名和密码登录 Jumpserver 了。
    # 用户首次登录 Jumpserver，会被要求完善用户信息，按照向导操作即可。
    注：MFA 即 Google Authenticator ，使用此软件需要APP时间与浏览器时间同步

.. image:: _static/img/admin_user.jpg

三、创建资产
``````````````````

3.1 创建 Linux 资产

3.1.1 编辑资产树

::

    # 节点不能重名，右击节点可以添加、删除和重命名节点，以及进行资产相关的操作
    注：如果有 linux 资产和 windows 资产，建议先建立 Linux 节点与 Windows 节点，不然授权时不好处理

.. image:: _static/img/asset_tree.jpg

3.1.2 创建管理用户

::

    # 管理用户是资产上的 root，或拥有 NOPASSWD: ALL sudo 权限的用户，Jumpserver 使用该用
    户来推送系统用户、获取资产硬件信息等

    # 如果使用ssh私钥管理资产，需要先在资产上设置，这里举个例子供参考（本例登录资产使用root为例）
    (1). 在资产上生成 root 账户的公钥和私钥

      $ ssh-keygen -t rsa  # 默认会输入公钥和私钥文件到 ~/.ssh 目录

    (2). 将公钥输出到文件 authorized_keys 文件，并修改权限

      $ cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
      $ chmod 400 ~/.ssh/authorized_keys

    (3). 打开RSA验证相关设置

      $ vim /etc/ssh/sshd_config

      RSAAuthentication yes
      PubkeyAuthentication yes
      AuthorizedKeysFile     .ssh/authorized_keys

    (4). 重启 ssh 服务
      $ service sshd restart

    (5). 上传 ~/.ssh 目录下的 id_rsa 私钥到 jumpserver 的管理用户中

    # 这样就可以使用 ssh私钥 进行管理服务器

    # 名称可以按资产树来命名。用户名root。密码和 SSH 私钥必填一个

.. image:: _static/img/create_asset_admin_user.jpg

3.1.3 创建系统用户

::

    # 系统用户是 Jumpserver 跳转登录资产时使用的用户，可以理解为登录资产用户
    # 系统用户的 Sudo 栏设定用户的 sudo 权限

    # 这里简单举几个例子
    Sudo /bin/su  # 当前系统用户可以免sudo密码执行sudo su命令

    Sudo /usr/bin/git,/usr/bin/php,/bin/cat,/bin/more,/bin/less,/usr/bin/tail
    # 当前系统用户可以免sudo密码执行git php cat more less tail

    Sudo !/usr/bin/yum  # 禁止执行 yum 权限

    # 此处的权限应该根据使用用户的需求汇总后定制，原则上给予最小权限即可

    # 下图为不允许用户执行一些危险的操作，允许其他的所有权限

.. image:: _static/img/create_user_sudo.jpg

::

    # 系统用户创建时，如果选择了自动推送 Jumpserver 会使用 Ansible 自动推送系统用户到资产中，
    如果资产(交换机、Windows )不支持 Ansible, 请手动填写资产上已有的账号及账号密码

    # 如果不想使用 Jumpserver 推送用户，请去掉自动生成密钥、自动推送勾选。手动填写资产上已有的账号及账号密码

    # 如果想让用户登录资产时自己输入密码，可以点击系统用户的名称 点击清除认证信息

.. image:: _static/img/create_asset_system_user.jpg

3.1.4 创建资产

::

    # 点击页面左侧的“资产管理”菜单下的“资产列表”按钮，查看当前所有的资产列表。
    # 点击页面左上角的“创建资产”按钮，进入资产创建页面，填写资产信息。
    # IP 地址和管理用户要确保正确，确保所选的管理用户的用户名和密码能"牢靠"地登录指定的 IP 主机上。
    资产的系统平台也务必正确填写。公网 IP 信息只用于展示，可不填，Jumpserver 连接资产使用的是 IP 信息。

.. image:: _static/img/create_asset.jpg

::

    # 资产创建信息填写好保存之后，可测试资产是否能正确连接
    注：被连接资产需要python组件，且版本大于等于2.6，Ubuntu等资产默认不允许root用户远程ssh登录，请自行处理

    # 如果资产不能正常连接，请检查管理用户的用户名和密钥是否正确以及该管理用户是否能使用 SSH 从 Jumpserver 主机正确登录到资产主机上

.. image:: _static/img/check_asset_connect.jpg

参考 `Linux 资产连接说明 <faq_linux.html>`_

3.1.5 网域列表

::

    # 网域功能是为了解决部分环境无法直接连接而新增的功能，原理是通过网关服务器进行跳转登录
    # 点击页面左侧的“网域列表”按钮，查看所有网域列表
    # 点击页面左上角的“创建网域”按钮，进入网域创建页面，选择资产里用作网域的网关服务器
    注：混合云适用

.. image:: _static/img/create_domain.jpg

::

    # 点击网域的名称，进入网域详情列表。
    # 点击页面的“网关”按钮，选择网关列表的“创建网关”按钮，进入网关创建页面，填写网关信息。
    # IP信息一般默认填写网域资产的IP即可（如用作网域的资产有多块网卡和IP地址，选能与jumpserer通信的任一IP即可）
    注：用户名与密码可以使用网关资产上已存在的任一拥有执行 ssh 命令权限的用户

.. image:: _static/img/create_geteway.jpg

::

    注：保存信息后点击测试连接，确定设置无误后到资产列表添加需要使用网关登录的资产即可。

.. image:: _static/img/create_asset02.jpg

3.2 创建 Windows 资产

3.2.1 创建 Windows 系统管理用户

::

    注：同 Linux 系统的管理用户一样，名称可以按资产树来命名，用户名是管理员用户名，密码是管理员的密码

.. image:: _static/img/create_windows_admin.jpg

3.2.2 创建 Windows 系统系统用户

::

    # 目前 Windows 暂不支持自动推送，用户必须在系统中存在且有权限使用远程连接，请确认资产的防火墙已经开放
    注：Windows 资产协议务必选择 rdp

    # 如果想让用户登录资产时自己输入密码，可以点击系统用户的名称 点击清除认证信息

.. image:: _static/img/create_windows_user.jpg

3.2.3 创建 Windows 资产

::

    # 同创建 Linux 资产一样。
    # 创建 Windows 资产，系统平台请选择正确的 Windows，默认 RDP 端口号为3389，IP 和 管理用户请正确选择，
    注：确保管理用户能正确登录到指定的 IP 主机上

.. image:: _static/img/create_windows_asset.jpg

参考 `Windows 资产连接说明 <faq_windows.html>`_

四、资产节点管理
``````````````````````

4.1 为资产树节点分配资产

::

    注：在资产列表页面，选择要添加资产的节点，右键，选择添加资产到节点(一台资产可以同时在多个节点下面)

.. image:: _static/img/add_asset_to_node.jpg

::

    注：选择要被添加的资产，点击"确认"即可。

.. image:: _static/img/select_asset_to_node.jpg

4.2 删除节点资产

::

    注：选择要被删除的节点，选择"从节点删除"，点击"提交"即可。

.. image:: _static/img/delete_asset_from_node.jpg

五、创建授权规则
`````````````````````

::

    # 节点，对应的是资产，代表该节点下的所有资产
    # 用户组，对应的是用户，代表该用户组下所有的用户
    # 系统用户，及所选的用户组下的用户能通过该系统用户使用所选节点下的资产
    # 节点，用户组，系统用户是一对一的关系，所以当拥有 Linux、Windows 不同类型资产时，
    应该分别给 Linux 资产和 Windows 资产创建授权规则。

.. image:: _static/img/create_auth_rules.jpg

::

    注：创建的授权规节点要与资产所在的节点一致。

.. image:: _static/img/auth_rule_list.jpg

::

    # 原则上，一个授权只能同时授予一个用户或者一个组
    # 意思是：把个人的资产授权给个人，把部门的资产授权给部门，把项目的资产授权给项目...
    # 职责不同，权限就不同，按照职责制定系统用户
    # 这样授权就不会乱

六、用户使用资产
`````````````````````

6.1 登录 Jumpserver

::

    # 用户只能看到自己被管理员授权了的资产，如果登录后无资产，请联系管理员进行确认

.. image:: _static/img/user_login_success.jpg

6.2 使用资产

6.2.1 连接资产

::

    # 点击页面左边的 Web 终端：

.. image:: _static/img/link_web_terminal.jpg

::

    # 打开资产所在的节点：

.. image:: _static/img/luna_index.jpg

::

    # 点击资产名字，就连上资产了，整个过程不需要用户输入资产的任何信息
    # 如果显示连接超时，请参考FAQ文档进行处理

.. image:: _static/img/windows_assert.jpg

6.2.2 断开资产

::

    # 点击页面顶部的 Server 按钮会弹出选个选项，第一个断开所选的连接，第二个断开所有连接。

.. image:: _static/img/disconnect_assert.jpg

以上就是 Jumpserver 的简易入门了，Jumpserver 还有很多功能等待您去发现。在使用过程中，如果遇到什么问题，可以在文档的"联系方式"一栏找到我们。
