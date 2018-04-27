FAQ
==========
.. toctree::
   :maxdepth: 1

   Windows 资产连接说明 <faq_windows.rst>
   Windows sftp使用说明 <faq_sftp.rst>
   二次认证（Google Auth）入口说明 <faq_googleauth.rst>


常见问题
~~~~~~~~~~~~~~~~~~~~~

1. Windows 资产连接错误排查思路

::

    (1). 如果白屏  检查nginx配置文件的guacamole设置ip是否正确，检查终端管理的gua状态是否在线，检查资产设置及系统用户是否正确；
    (2). 如果显示没有权限 可能是你在 终端管理里没有接受 guacamole的注册，请接受一下，然后重启guacamole
    (3). 如果显示未知问题 可能是你的资产填写的端口不对，或者授权的系统用户的协议不是rdp
    (4). 提示无法连接服务器，请联系管理员或查看日志 一般情况下是登录的系统账户不正确，可以从Windows的日志查看信息（资产的信息填写不正确也会报这个错误）
    (5). 提示网络问题无法连接或者超时，请检查网络连接并重试，或联系管理员 一般情况下是防火墙设置不正确，可以从Windows的日志查看信息（资产的信息填写不正确也会报这个错误）

2. Linux 资产连接错误排查思路

::

    (1). 检查管理用户的权限是否正确，权限需要与root权限一致。
    (2). 检查资产的防火墙策略，可以在资产上面新建个用户，尝试用此用户进行ssh连接。
    (3). 检查资产的python，确定版本不小于2.6，不高于3.x。
    (4). 检查资产的ssh策略，确保可以被jumpserver应用访问。

3. 用户、系统用户、管理用户的关系

::

    用户：每个公司的同事创建一个用户账号，用来登录Jumpserver
    系统用户：使用来登录到服务器的用户，如 web, dba, root等，配合sudo实现权限管控
    管理用户：是服务器上已存在的特权用户，Ansible用来获取硬件信息, 如 root, 或者其它拥有 sudo NOPASSWD: ALL权限的用户

    (1). 这里解释一下系统用户里面的sudo，比如有个系统用户的权限是这样的：

    Sudo: /usr/bin/git,/usr/bin/php,/bin/cat,/bin/more,/bin/less,/usr/bin/head,/usr/bin/tail
    意思是允许这个系统用户免密码执行 git、PHP、cat、more、less、head、tail 命令，只要关联了这个系统用户的用户在相应的资产都可以执行这些命令。

4. coco或guacamole注册失败，或重新注册方法

::

    (1). 在 Jumpserver后台 会话管理 - 终端管理  删掉它们

    (2). coco 重新注册（注意虚拟环境 source /opt/py3/bin/activate）

      $ cd /opt/coco && ./cocod stop
      $ rm /opt/coco/keys/.access_key  # coco, 如果你是按文档安装的，key应该在这里
      $ ./cocod start -d  # 正常运行后到Jumpserver 会话管理-终端管理 里面接受coco注册

   (3). guacamole重新注册

      $ docker stop jms_guacamole  # 如果名称更改过或者不对，请使用docker ps 查询容器的 CONTAINER ID ，然后docker stop <CONTAINER ID>
      $ docker rm jms_guacamole  # 如果名称更改过或者不对，请使用docker ps -a 查询容器的 CONTAINER ID ，然后docker rm <CONTAINER ID>
      $ rm /opt/guacamole/key/*  # guacamole, 如果你是按文档安装的，key应该在这里
      $ systemctl stop docker
      $ systemctl start docker
      $ docker run --name jms_guacamole -d \
        -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
        -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
        -e JUMPSERVER_SERVER=http://<填写jumpserver的url地址> \
        registry.jumpserver.org/public/guacamole:latest

      # 如果registry.jumpserver.org/public/guacamole:latest下载很慢，可以换成jumpserver/guacamole:latest

      # 正常运行后到Jumpserver 会话管理-终端管理 里面接受gua注册
      $ docker restart jms_guacamole  # 如果接受注册后显示不在线，重启gua就好了

5. Ansible报错汇总

::

    (1). 资产是centos5.x Python版本 2.4，

        $ yum -y install python26
        $ mv /usr/bin/python /usr/bin/python.bak
        $ ln -s /usr/bin/python2.6 /usr/bin/python

        # 修改 /bin/yum 使用原来的python
        $ sed -i 's@/usr/bin/python$@/usr/bin/python2.4@g' /bin/yum

6. input/output error, 通常jumpserver所在服务器字符集问题

::

    # Centos7
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG=zh_CN.UTF-8' > /etc/locale.conf

    # Centos6
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG=zh_CN.UTF-8' > /etc/sysconfig/i18n

    如果任然报input/output error，尝试执行 yum update 后重启服务器（仅测试中参考使用，实际运营服务器请谨慎操作）

7. 运行 sh make_migrations.sh 报错，
    CommandError: Conflicting migrations detected; multiple ... django_celery_beat ...
    这是由于 django-celery-beat老版本有bug引起的

::

    $ rm -rf /opt/py3/lib/python3.6/site-packages/django_celery_beat/migrations/
    $ pip uninstall django-celery-beat
    $ pip install django-celery-beat

8. 连接测试常见错误

::

    (1). to use the 'ssh' connection type with passwords, you mast install the sshpass program

        # Centos
        $ yum -y install sshpass

        # Ubuntu
        $ apt-get -y install sshpass

    注意，在 coco 服务器上面安装完成后需要重启服务。

    (2). Authentication failure

        # 一般都是资产的管理用户不正确

    (3). Failed to connect to the host via ssh: ssh_exchange_identification: read: Connection reset by peer\r\n

        # 一般是资产的 ssh 或者 防火墙 做了限制，无法连接资产（资产信息填错也可能会报这个错误）

    (4). "MODULE FAILURE","module_stdout":"/bin/sh: 1: /usr/bin/python: not found\r\n","module_stderr":"Shared connection to xx.xx.xx.xx closed.\r\n"

        # 一般是资产 python 未安装或者 python 异常

9. 其他问题

::

    (1). 邮箱设置 新建用户无法收到邮件需要重启一次jumpserver（系统设置修改需要重启的问题后面会修正）

    (2). 收到的邮件链接地址是 localhost 可以到 系统设置-基本设置 里面修改url，保存后重启即可

    (3). coco 提示[service ERROR] Failed register terminal jzsas exist already
        # 参考上面的coco重新注册方法

    (4). guacamole 不在线
        # 尝试重启一下guacamole，然后再看看，如果任然不在线，参考上面gua重新注册的方法
        $ docker restart jms_guacamole  # 如果容器的名称不对，请用docker ps查询

    (5). LDAP设置 测试通过，但是登录失败需要检查用户的ou是否正确，如果使用用户cn作为登录用户名，请确认用户的cn属性不是中文

    (6). Luna 打开网页提示403 Forbidden错误，一般是nginx配置文件的luna路径不正确或者luna下载了源代码，请重新下载编译好的代码

    (7). Luna 打开网页提示502 Bad Gateway错误，一般是selinux和防火墙的问题，请根据nginx的errorlog来检查

    (8). 默认录像存储位置在jumpserver/data/media

    (9). 录像存储在阿里云oss的规则，Jumpserver 系统设置-终端设置 录像存储
        {"default": {"TYPE": "server"}, "cn-north-1": {"TYPE": "s3", "BUCKET": "jumpserver", "ACCESS_KEY": "", "SECRET_KEY": "", "REGION": "cn-north-1"}, "ali-oss": {"TYPE": "oss", "BUCKET": "jumpserver", "ACCESS_KEY": "", "SECRET_KEY": "", "ENDPOINT": "http://oss-cn-hangzhou.aliyuncs.com"}}

        修改后，需要修改nginx配置文件
        location /media/ {
        add_header Content-Encoding gzip;
        proxy_pass http://oss-cn-hangzhou.aliyuncs.com;
        }

        还需要在Jumpserver 会话管理-终端管理 修改terminal的配置 录像存储

    (10). 管理密码忘记了或者重置管理员密码
        $ source /opt/py3/bin/activate
        $ cd /opt/jumpserver/apps
        $ python manage.py changepassword  <user_name>

        # 新建超级用户的命令如下命令
        $ python manage.py createsuperuser --username=user --email=user@domain.com

    (11). 清理celery产生的数据(无法正常推送及连接资产可以使用)
        $ source /opt/py3/bin/activate
        $ cd /opt/jumpserver/apps
        $ python manage.py shell
        $ from celery.task.control import discard_all
        $ discard_all()
        $ exit()
        $ cd /opt/jumpserver
        $ ./jms restart celery
