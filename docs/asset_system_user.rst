系统用户
===========

这里介绍系统用户功能。

.. contents:: Topics

.. _view_admin_system_user:

查看系统用户
````````````

点击页面左侧“资产管理“菜单下的”系统用户“按钮，进入系统用户列表页面，查看系统用户的名称，资产数和连接数等信息。

.. _create_admin_system_user:

创建系统用户
````````````

系统用户是 Jumpserver 跳转登录资产时使用的用户，可以理解为登录资产用户，如 web, sa, dba(`ssh web@some-host`), 而不是使用某个用户的用户名跳转登录服务器（`ssh xiaoming@some-host`）; 简单来说是 用户使用自己的用户名登录 Jumpserver, Jumpserver 使用系统用户登录资产。

系统用户创建时，如果选择了自动推送 Jumpserver 会使用 Ansible 自动推送系统用户到资产中，如果资产（交换机、Windows）不支持 Ansible, 请手动填写账号密码。

Linux 系统协议项务必选择 ssh 。如果用户在系统中已存在，请去掉自动生成密钥、自动推送勾选。

.. image:: _static/img/create_asset_system_user.jpg

.. _update_admin_system_user:

创建 Windows 系统系统用户

由于目前 Windows 不支持自动推送，所以 Windows 的系统用户设置成与管理用户同一个用户。

Windows 资产协议务必选择 rdp。

.. image:: _static/img/create_windows_user.jpg

更新系统用户
`````````````

点击页面动作栏的“更新”按钮，进入更新系统用户页面，编辑系统用户信息，点击“提交”按钮，系统用户更新完成。

.. _delete_admin_system_user:

删除系统用户
`````````````

点击页面动作栏的“删除”按钮，弹出删除确认框，点击“删除”按钮，完成删除系统用户。