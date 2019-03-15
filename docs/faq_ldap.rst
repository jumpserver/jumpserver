LDAP 使用说明
------------------------------

-  LDAP 支持 使用 LADP 与 Windows AD 的用户作为 jumpserver 登录用户
-  已经存在的用户不能与要登录的 LDAP 用户有用户名和邮箱同名, 具有唯一性

1. LDAP 设置说明

.. code-block:: vim

    LDAP地址  ldap://serverurl:389  或者  ldaps://serverurl:636(需要勾选ssl)
    # 此处是设置LDAP的服务器,推荐使用IP, 防止解析问题

    绑定DN  cn=administrator,cn=Users,dc=jumpserver,dc=org
    # 这里是设置认证用户的信息, jumpserver会使用这个用户去校验ldap的信息是否正确

    密码   # 上面认证用户的密码

    用户OU  ou=jumpserver,dc=jumpserver,dc=org
    # 这里是设置用来登录jumpserver的组织单元, 比如我要用某个ou的用户来登录jumpserver
    # 多OU用法  ou=jumpserver,dc=jumpserver,dc=org | ou=user,dc=jumpserver,dc=org | ou=xxx,dc=jumpserver,dc=org

    用户过滤器  (cn=%(user)s)
    # 这里是设置筛选ldap用户的哪些属性, 不能有多余的空格

    LADP属性映射  {"username": "cn", "name": "sn", "email": "mail"}
    username name email 是jumpserver的用户属性(不可更改)
    cn       sn   mail  是ldap的用户属性(可自定义)
    # 这里的意思是, 把ldap用户的属性映射到jumpserver上

    使用SSL
    # 勾选后 LDAP地址 需要设置成 ldaps://serverurl:636

    启动LDAP认证
    # 如果需要使用 LDAP或域用户 登录 jumpserver,则必选

2. 补充

.. code-block:: vim

    DN 一定要是完整的DN, 不能跳过OU, 可以使用其他工具查询
    如：cn=admin,ou=aaa,dc=jumpserver,dc=org,必须要写成cn=admin,ou=aaa,dc=jumpserver,dc=org 不能缩写成cn=admin,dc=jumpserver,dc=org

    用户OU 用户OU可以只写顶层OU, 不写子OU
    如：ou=aaa,ou=bbb,ou=ccc,dc=jumpserver,dc=org,可以只写ou=ccc,dc=jumpserver,dc=org,根据需求自行修改

    用户过滤器  筛选用户的规则, 点击测试连接就是根据这个规则到用户OU里面去检索用户, 可以自定义规则
    如：(uid=%(user)s) 或 (sAMAccountName=%(user)s)  等, 这里的属性需要与下面的属性映射设置一致

    LADP属性映射  username name email 这三项不可修改删除, 属性映射的字段必须存在, 且登录用户名和邮件不可以重复
    如：{"username": "uid", "name": "sn", "email": "mail"} 或 {"username": "sAMAccountName", "name": "cn", "email": "mail"}
    "username": "uid" 这里的 uid 必须和上面的 (uid=%(user)s) 这里的 uid 一致
    如果上面是(sAMAccountName=%(user)s) 那么下面也应该修改为{"username": "sAMAccountName",
    username 是 jumpserver 的用户用户名, name 是 jumpserver 的用户名称, mail 是 jumpserver 用户的邮箱
    属性映射的意思是把ldap的什么属性来作为jumpserver的用户用户名, 把ldap的什么属性作为jumpserver的用户名称, 把ldap的什么属性作为jumpserver的用户邮箱
