个人信息
=========

1.1 查看个人信息

个人信息页面展示了用户的名称、角色、邮件、所属用户组、SSh 公钥、创建日期、最后登录日期和失效日期等信息：

.. image:: _static/img/user_info.jpg

1.2 修改密码

在个人信息页面点击"重置密码"按钮，跳转到修改密码页面，正确输入新旧密码，即可完成密码修改:

.. image:: _static/img/user_update_password.jpg

1.3 修改 SSH 公钥

点击"重置 SSH 密钥"按钮，跳转到修改 SSH 密钥信息页，复制 SSH 密钥信息到指定框中，即可完成 SSH 密钥修改：

查看 SSH 公钥信息：

::

    $ cat ~/.ssh/id_rsa.pub
    ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDadDXxxx......

.. image:: _static/img/user_update_ssh_key.jpg