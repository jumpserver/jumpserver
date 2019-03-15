快速入门
==================

说明
``````````
- 到 Jumpserver 会话管理-终端管理 查看 Coco Guacamole 等应用是否在线

一、系统设置
````````````````````

**1.1 基本设置**
----------------

.. code-block:: vim

    # 修改 url 的"localhost"为你的实际 url 地址, 否则邮件收到的地址将为"localhost" 也无法创建新用户

.. image:: _static/img/basic_setting.jpg

**1.2 邮件设置**
----------------

.. code-block:: vim

    # 点击页面上边的"邮件设置", 进入邮件设置页面
    # 默认使用 25 端口, 不勾选 SSL 和 TLS; 如果需要勾选 SSL, 端口需要修改成 465; 如果需要勾选 TLS, 端口需要改成 587
    # 不可以同时勾选 SSL 和 TLS
    # 配置邮件服务后, 点击页面的"测试连接"按钮, 如果配置正确, Jumpserver 会发送一条测试邮件到您的 SMTP 账号邮箱里面, 确定收到测试邮件后点击保存即可使用

.. image:: _static/img/smtp_setting.jpg

**1.3 LDAP设置**
-----------------

.. code-block:: vim

    # 如果不需要使用"ldap"用户登陆 jumpserver, 可以直接跳过, 不需要设置
    # 先"测试"通过才能保存
    # DN 和 OU 一定要完整(如 "DN:cn=Manage,ou=Jumpserver,dc=jumpserver,ou=org")
    # 注：可借用第三方 gui 工具查看 ldap 用户的属性, 新版本已经支持中文名登录, 即cn=中文也可正常使用

.. image:: _static/img/ldap_setting.jpg

参考 `LDAP 使用说明 <faq_ldap.html>`_

**1.4 终端设置**
----------------

.. code-block:: vim

    # "密码认证"和"密钥认证"是 SSH 连接跳板机时所使用的认证方式(都不选会造成无法使用 SSH 方式连接登录跳板机, 不影响 web 登录)
    # "命令存储""录像存储"位置设置
    # "Telnet成功正则表达式" telnet设备登陆失败需要设置

    # 修改后, 需要修改在Jumpserver 会话管理-终端管理 修改terminal的配置 录像存储 命令记录, 然后重启 Jumpserver 服务
    # 设置后重启 Coco 才能生效

**1.5 安全设置**
----------------

.. code-block:: vim

    # "MAF二次认证"勾选会开启全局强制"MFA", 所有jumpserver用户必须使用动态口令进行认证登录(即时生效)
    # "限制登录失败"和"限制登录时间"设置需要重启jumpserver才能生效
    # "SSH最大空闲时间"设置需要重启jumpserver才能生效
    # "密码校验规则"设置立即生效

二、用户管理
`````````````````````

**2.1 创建 Jumpserver 用户**
----------------------------

.. code-block:: vim

    # 点击页面左侧"用户列表"菜单下的"用户列表", 进入用户列表页面
    # 点击页面左上角"创建用户"按钮, 进入创建用户页面, (也可以通过右上角导入模版进行用户导入)
    # 其中, 用户名即 Jumpserver 登录账号(具有唯一性, 不能重名)。名称为页面右上角用户标识(可重复)
    # 成功提交用户信息后, Jumpserver 会发送一条设置"用户密码"的邮件到您填写的用户邮箱
    # 点击邮件中的设置密码链接, 设置好密码后, 您就可以用户名和密码登录 Jumpserver 了。
    # 用户首次登录 Jumpserver, 会被要求完善用户信息, 按照向导操作即可。
    注：MFA 即 Google Authenticator, 使用此软件需要APP时间与浏览器时间同步

.. image:: _static/img/admin_user.jpg

三、资产管理
``````````````````

**3.1 创建 Linux 资产**
------------------------

**3.1.1 编辑资产树**

.. code-block:: vim

    # 节点不能重名, 右击节点可以添加、删除和重命名节点, 以及进行资产相关的操作
    # 注：如果有 linux 资产和 windows 资产, 建议先建立 Linux 节点与 Windows 节点, 不然授权时不好处理

.. image:: _static/img/asset_tree.jpg

**3.1.2 创建管理用户**

.. code-block:: shell

    # "管理用户"是资产上的 root, 或拥有 NOPASSWD: ALL sudo 权限的用户, Jumpserver 使用该用
    户来推送系统用户、获取资产硬件信息等

    # 如果使用ssh私钥管理资产, 需要先在资产上设置, 这里举个例子供参考(本例登录资产使用root为例)
    (1). 在资产上生成 root 账户的公钥和私钥

      $ ssh-keygen -t rsa  # 默认会输入公钥和私钥文件到 ~/.ssh 目录

    (2). 将公钥输出到文件 authorized_keys 文件, 并修改权限

      $ cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
      $ chmod 400 ~/.ssh/authorized_keys

    (3). 打开RSA验证相关设置

      $ vi /etc/ssh/sshd_config

      RSAAuthentication yes
      PubkeyAuthentication yes
      AuthorizedKeysFile     .ssh/authorized_keys

    (4). 重启 ssh 服务
      $ service sshd restart

    (5). 上传 ~/.ssh 目录下的 id_rsa 私钥到 jumpserver 的管理用户中

    # 这样就可以使用 ssh私钥 进行管理服务器
    # 名称可以按资产树来命名。用户名root。密码和 SSH 私钥必填一个

.. image:: _static/img/create_asset_admin_user.jpg

**3.1.3 创建系统用户**

.. code-block:: vim

    # "系统用户"是 Jumpserver 跳转登录资产时使用的用户, 用户使用该用户登录资产
    # "自动生成密码"、"自动推送"、"Sudo"等功能需要对应资产的"管理用户"有root权限, 否则自动推送失败
    # "系统用户"的"Sudo"栏设定用户的sudo权限
    # 如果创建的"系统用户"已在资产上面存在, "推送"将会覆盖掉原用户的"home"目录权限(注: 替换成700权限)

    # 这里简单举几个例子
    Sudo /bin/su  # 当前系统用户可以免sudo密码执行sudo su命令

    Sudo /usr/bin/git, /usr/bin/php, /bin/cat, /bin/more, /bin/less, /usr/bin/tail
    # 当前系统用户可以免sudo密码执行git php cat more less tail

    Sudo !/usr/bin/yum  # 禁止执行 yum 权限

    # 此处的权限应该根据使用用户的需求汇总后定制, 原则上给予最小权限即可

    # 下图为不允许用户执行一些危险的操作, 允许其他的所有权限

.. image:: _static/img/create_user_sudo.jpg

.. code-block:: vim

    # "系统用户"创建时, 如果选择了"自动推送" Jumpserver 会使用"Ansible"自动推送系统用户到资产中,
    # 如果资产(交换机、Windows)不支持"Ansible", 请去掉"自动生成密钥"、"自动推送"勾选。手动填写资产上已有的账号及账号密码

    # 如果想让用户登录资产时自己输入密码, 可以在创建系统用户时选择"手动登录"

.. image:: _static/img/create_asset_system_user.jpg

**3.1.4 创建资产**

.. code-block:: vim

    # 点击页面左侧的"资产管理"菜单下的"资产列表"按钮, 查看当前所有的资产列表。
    # 点击页面左上角的"创建资产"按钮, 进入资产创建页面, 填写资产信息。
    # IP 地址和管理用户要确保正确, 确保所选的管理用户的用户名和密码能"牢靠"地登录指定的 IP 主机上。
    # 资产的系统平台也务必正确填写。公网 IP 信息只用于展示, 可不填, Jumpserver 连接资产使用的是 IP 信息。

.. image:: _static/img/create_asset.jpg

.. code-block:: vim

    # 资产创建信息填写好保存之后, 可"测试资产"是否能正确连接
    注：被连接资产需要"python"组件, 且版本大于等于2.6, Ubuntu等资产默认不允许root用户远程ssh登录, 请自行处理

    # 如果资产不能正常连接, 请检查"管理用户"的用户名和密钥是否正确以及该"管理用户"是否能使用 SSH 从 Jumpserver 主机正确登录到资产主机上

.. image:: _static/img/check_asset_connect.jpg

参考 `SSH协议 资产连接说明 <faq_ssh.html>`_

**3.2 创建 Windows 资产**
-------------------------

**3.2.1 创建 Windows 系统管理用户**

.. code-block:: vim

    注：同 Linux 系统的"管理用户"一样, 名称可以按"资产树"来命名, 用户名是管理员用户名, 密码是管理员的密码

.. image:: _static/img/create_windows_admin.jpg

**3.2.2 创建 Windows 系统系统用户**

.. code-block:: vim

    # 目前 Windows 暂不支持"自动推送", 用户必须在系统中存在且有权限使用"远程连接", 请确认资产的"防火墙"已经开放
    注："Windows 资产"协议务必选择"rdp"

    # 如果想让用户登录资产时自己输入密码, 可以在"系统用户"设置"手动登录"

.. image:: _static/img/create_windows_user.jpg

**3.2.3 创建 Windows 资产**

.. code-block:: vim

    # Windows 7/8/2008/2012 "系统平台"选择 "Windows"
    # Windows 10/2016 "系统平台"选择 "Windows(2016)"
    # 创建 Windows 资产, "系统平台"请选择正确的 Windows, 默认"RDP"端口号为 3389, "IP" 和"管理用户"请正确选择
    # 注：确保"管理用户"能正确登录到指定的 IP 主机上

.. image:: _static/img/create_windows_asset.jpg

参考 `RDP协议 资产连接说明 <faq_rdp.html>`_

**3.3 网域列表**
----------------

.. code-block:: vim

    # "网域"功能是为了解决部分环境无法直接连接而新增的功能, 原理是通过网关服务器进行跳转登录
    # 点击页面左侧的"网域列表"按钮, 查看所有网域列表
    # 点击页面左上角的"创建网域"按钮, 进入网域创建页面, 选择资产里用作网域的网关服务器
    # 注：混合云适用

.. image:: _static/img/create_domain.jpg

.. code-block:: vim

    # 点击"网域"的名称, 进入"网域详情"列表。
    # 点击页面的"网关"按钮, 选择网关列表的"创建网关"按钮, 进入网关创建页面, 填写网关信息。
    # IP信息一般默认填写网域资产的IP即可(如用作网域的资产有多块网卡和IP地址, 选能与jumpserer通信的任一IP即可)
    注：用户名与密码可以使用网关资产上已存在的任一拥有执行 ssh 命令权限的用户

.. image:: _static/img/create_geteway.jpg

.. code-block:: vim

    注: 保存信息后点击"测试连接", 确定设置无误后到资产列表添加需要使用"网关"登录的资产即可。
    注: "Windows资产"可以使用"ssh网关"

.. image:: _static/img/create_asset02.jpg

**3.4 资产节点管理**
---------------------

**3.4.1 为资产树节点分配资产**

.. code-block:: vim

    # 在"资产列表"页面, 选择要添加资产的"节点", 右键, 选择添加资产到"节点"(一台资产可以同时在多个节点下面)

.. image:: _static/img/add_asset_to_node.jpg

.. code-block:: vim

    # 选择要被添加的"资产", 点击"确认"即可。

.. image:: _static/img/select_asset_to_node.jpg

**3.4.2 删除节点资产**

.. code-block:: vim

    # 选择要被删除的节点, 选择"从节点删除", 点击"提交"即可。

.. image:: _static/img/delete_asset_from_node.jpg

四、创建授权规则
`````````````````````

**4.1 为用户分配资产**
----------------------

.. code-block:: vim

    # "名称", 授权的名称, 不能重复
    # "用户"和"用户组"二选一, 不推荐即选择用户又选择用户组
    # "资产"和"节点"二选一, 选择节点会包含节点下面的所有资产
    # "系统用户", 及所选的用户或用户组下的用户能通过该系统用户使用所选节点或者节点下的资产
    # 用户(组), 资产(节点), 系统用户是一对一的关系, 所以当拥有 Linux、Windows 不同类型资产时,
    # 应该分别给 Linux 资产和 Windows 资产创建授权规则。

资产授权与节点授权的区别请参考下面示例, 一般情况下, 资产授权给个人, 节点授权给用户组, 一个授权只能选择一个系统用户

.. image:: _static/img/create_auth_rules01.jpg
.. image:: _static/img/create_auth_rules02.jpg

.. code-block:: vim

    注：创建的授权规则, 节点要与资产所在的节点一致

.. image:: _static/img/auth_rule_list.jpg

.. code-block:: vim

    # 原则上, 一个授权只能同时授予一个用户或者一个组
    # 意思是：把个人的资产授权给个人, 把部门的资产授权给部门, 把项目的资产授权给项目...

五、用户使用资产
`````````````````````

**5.1 登录 Jumpserver**
-----------------------

.. code-block:: vim

    # 用户只能看到自己被管理员授权了的"资产", 如果登录后无资产, 请联系管理员进行确认

.. image:: _static/img/user_login_success.jpg

**5.2 使用资产**
----------------

**5.2.1 连接资产**

.. code-block:: vim

    # 点击页面左边的 "Web 终端"

.. image:: _static/img/link_web_terminal.jpg

.. code-block:: vim

    # 打开资产所在的节点：

.. image:: _static/img/luna_index.jpg

.. code-block:: vim

    # 点击"资产"名字, 就连上资产了, 整个过程不需要用户输入资产的任何信息
    # 如果显示连接超时, 请参考FAQ文档进行处理

.. image:: _static/img/windows_assert.jpg

**5.2.2 断开资产**

.. code-block:: vim

    # 点击页面顶部的"Server"按钮会弹出选个选项, 第一个断开所选的连接, 第二个断开所有连接。

.. image:: _static/img/disconnect_assert.jpg

以上就是 Jumpserver 的简易入门了, Jumpserver 还有很多功能等待您去发现。在使用过程中, 如果遇到什么问题, 可以在文档的"联系方式"一栏找到我们。
