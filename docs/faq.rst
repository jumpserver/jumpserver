FAQ
==========

1. Windows 无法连接

::

    (1). 如果白屏  可能是nginx设置的不对，也可能运行guacamole的docker容器有问题，总之请求到不了guacamole
    (2). 如果显示没有权限 可能是你在 终端管理里没有接受 guacamole的注册，请接受一下，如果还是不行，就删除刚才的注册，重启guacamole的docker重新注册
    (3). 如果显示未知问题 可能是你的资产填写的端口不对，或者授权的系统用户的协议不是rdp


2. 用户、系统用户、管理用户的关系

::

    用户：每个公司的同事创建一个用户账号，用来登录Jumpserver
    系统用户：使用来登录到服务器的用户，如 web, dba, root等
    管理用户：是服务器上已存在的特权用户，Ansible用来获取硬件信息, 如 root, 或者其它拥有 sudo NOPASSWD: ALL权限的用户


3. coco或guacamole 注册失败，或重新注册方法

::

   (1). 停止 coco 或 删掉guacamole的docker

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


6. 运行 sh make_migrations.sh 报错，
   CommandError: Conflicting migrations detected; multiple ... django_celery_beat ...
   这是由于 django-celery-beat老版本有bug引起的

::

   $ rm -rf /opt/py3/lib/python3.6/site-packages/django_celery_beat/migrations/
   $ pip uninstall django-celery-beat
   $ pip install django-celery-beat