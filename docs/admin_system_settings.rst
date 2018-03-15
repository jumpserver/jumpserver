系统设置
=============

这里介绍系统设置的功能。

.. contents:: Topics

.. _view_system_settings:

查看系统设置
`````````````

点击页面左侧“系统设置”按钮，进入系统设置页面，产看基本设置、邮件设置、LDAP 设置和终端设置等内容。

.. _basic_settings:

基本设置
`````````

点击页面上边的"基本设置" TAB ，进入基本设置页面，编辑当前站点 URL、用户想到 URL、Email 主题前缀等信息，点击“提交”按钮，基本设置完成。

.. _email_settings:

邮件设置
`````````

点击页面上边的"邮件设置" TAB ，进入邮件设置页面，编辑 SMTP 主机、SMTP 端口、SMTP 账号、SMTP 密码和使用 SSL 或者 TSL 等信息，点击“测试连接”按钮，测试是否正确设置，点击“提交”按钮，邮件设置完成。

.. _ladp_settings:

LDAP 设置
````````````

点击页面上边的" LDAP 设置" TAB ，进入 LDAP 设置页面，编辑 LDAP 地址、DN、用户 OU、用户过滤器、LDAP 属性映射和是否使用 SSL、是否启用 LDAP 认证等信息，点击“测试连接”按钮，测试是否正确设置，点击“提交”按钮，完成 LDAP 设置。

如果这里有问题请手动用 ldapsearch命令测试一下, 如果能唯一搜索出这个用户代表你的设置是对的，然后根据用户的属性填写映射关系

.. image:: _static/img/ldapsearch.png
    :alt: LDAP搜索实例

::

   # 注意下面的 testuser对应的是你ldap server上存在的用户，填写到配置中需要改为 %(user)s
   ldapsearch -x -W -h ldap://127.0.0.1:389 -b "ou=People,dc=xxx,dc=com" -D "cn=admin,dc=xxx,dc=com" "(cn=testuser)"
   ldapsearch -x -W -h ldap://127.0.0.1:389 -b "dc=xxx,dc=com" -D "cn=admin,dc=xxx,dc=com" "(&(cn=testuser)(objectClass=account))"

   # extended LDIF
   #
   # LDAPv3
   # base <ou=People,dc=xxx,dc=com> with scope subtree
   # filter: (cn=*)
   # requesting: ALL
   #

   # testuser, People, xxx.com
   dn: uid=testuser,ou=People,dc=xxx,dc=com
   uid: testuser       # 打算使用该属性映射为jumpserver username
   cn: testuser        # 打算使用该属性映射为jumpserver name
   mail: xyz@google.coom   # 打算使用该属性映射为jumpserver email
   objectClass: account
   objectClass: posixAccount
   objectClass: top
   objectClass: shadowAccount
   ...



.. _terminal_settings:

终端设置
````````````

点击页面上边的“终端设置” TAB ，进入终端设置页面，编辑终端信息，点击“提交”按钮，终端设置完成。