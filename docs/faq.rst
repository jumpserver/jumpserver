FAQ
==========

1. Windows 无法连接

::

    (1). 如果白屏  可能是nginx设置的不对，也可能运行guacamole的docker容器有问题，总之请求到不了guacamole
    (2). 如果显示没有权限 可能是你在 终端管理里没有接受 guacamole的注册，请接受一下，如果还是不行，就删除刚才的注册，重启guacamole的docker重新注册
    (3). 如果显示未知问题 可能是你的资产填写的端口不对，或者授权的系统用户的协议不是rdp
    (4). 提示无法连接服务器，请联系管理员或查看日志 一般情况下是登录的系统账户不正确，可以从Windows的日志查看信息
    (5). 提示网络问题无法连接或者超时，请检查网络连接并重试，或联系管理员 一般情况下是防火墙设置不正确，可以从Windows的日志查看信息


2. 用户、系统用户、管理用户的关系

::

    用户：每个公司的同事创建一个用户账号，用来登录Jumpserver
    系统用户：使用来登录到服务器的用户，如 web, dba, root等，配合sudo实现权限管控
    管理用户：是服务器上已存在的特权用户，Ansible用来获取硬件信息, 如 root, 或者其它拥有 sudo NOPASSWD: ALL权限的用户

    (1). 这里解释一下系统用户里面的sudo，比如有个系统用户的权限是这样的：

    Sudo: /usr/bin/git,/usr/bin/php,/bin/cat,/bin/more,/bin/less,/usr/bin/head,/usr/bin/tail
    意思是允许这个系统用户使用 git、PHP、cat、more、less、head、tail 命令，只要关联了这个系统用户的用户在相应的资产都可以执行这些命令。

3. coco或guacamole 注册失败，或重新注册方法

::

   (1). 停止 coco 或 删掉 guacamole 的docker

      $ kill <coco的pid>
      $ docker rm -f <guacamole docker的id>

   (2). 在 Jumpserver后台 会话管理 - 终端管理  删掉它们

   (3). 删掉它们曾经注册的key

      $ rm keys/.access_key  # coco
      $ rm /opt/guacamole/key/*  # guacamole, 如果你是按文档安装的，key应该在这里


4. Ansible报错汇总

::

   (1). 资产是centos5.x Python版本 2.4，

       $ yum -y install python26
       $ mv /usr/bin/python /usr/bin/python.bak
       $ ln -s /usr/bin/python2.6 /usr/bin/python

       # 修改 /bin/yum 使用原来的python
       $ sed -i 's@/usr/bin/python$@/usr/bin/python2.4@g' /bin/yum


5. input/output error, 通常jumpserver所在服务器字符集问题(一下修改方法仅限 centos7)

::

   $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
   $ export LC_ALL=zh_CN.UTF-8
   $ echo 'LANG=zh_CN.UTF-8' > /etc/sysconfig/i18n


<<<<<<< HEAD
6. 运行 sh make_migrations.sh 报错，
   CommandError: Conflicting migrations detected; multiple ... django_celery_beat ...
   这是由于 django-celery-beat老版本有bug引起的

::

   $ rm -rf /opt/py3/lib/python3.6/site-packages/django_celery_beat/migrations/
   $ pip uninstall django-celery-beat
   $ pip install django-celery-beat
=======
6. 连接测试常见错误

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

       # 一般是资产的 ssh 或者 防火墙 做了限制

   (4). "MODULE FAILURE","module_stdout":"/bin/sh: 1: /usr/bin/python: not found\r\n","module_stderr":"Shared connection to xx.xx.xx.xx closed.\r\n"

       # 一般是资产 python 未安装或者 python 异常，此问题多发生在 ubuntu 资产上
>>>>>>> github/docs
