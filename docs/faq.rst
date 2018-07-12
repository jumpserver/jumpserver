FAQ
==========
.. toctree::
   :maxdepth: 1

   Sftp使用说明 <faq_sftp.rst>
   安装过程常见问题 <faq_install.rst>
   Linux 资产连接说明 <faq_linux.rst>
   Windows 资产连接说明 <faq_windows.rst>
   二次认证（Google Auth）入口说明 <faq_googleauth.rst>


其他问题
~~~~~~~~~~~~~~~~~~~~~

1. 用户、系统用户、管理用户的关系

::

    用户：每个公司的同事创建一个用户账号，用来登录Jumpserver
    系统用户：使用来登录到服务器的用户，如 web, dba, root等，配合sudo实现权限管控
    管理用户：是服务器上已存在的特权用户，Ansible用来获取硬件信息, 如 root, 或者其它拥有 sudo NOPASSWD: ALL权限的用户

    # 这里解释一下系统用户里面的sudo，比如有个系统用户的权限是这样的：

    Sudo: /usr/bin/git,/usr/bin/php,/bin/cat,/bin/more,/bin/less,/usr/bin/head,/usr/bin/tail
    意思是允许这个系统用户免密码执行 git、PHP、cat、more、less、head、tail 命令，只要关联了这个系统用户的用户在相应的资产都可以执行这些命令。

2. input/output error, 通常jumpserver所在服务器字符集问题

::

    # Centos7
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf

    # Centos6
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/sysconfig/i18n

    # Ubuntu
    $ apt-get install language-pack-zh-hanscd
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/default/locale

    如果任然报input/output error，尝试执行 yum update 后重启服务器（仅测试中参考使用，实际运营服务器请谨慎操作）

3. luna 无法访问

::

    # Luna 打开网页提示403 Forbidden错误，一般是nginx配置文件的luna路径不正确或者luna下载了源代码，请重新下载编译好的代码

    # Luna 打开网页提示502 Bad Gateway错误，一般是selinux和防火墙的问题，请根据nginx的errorlog来检查

4. 录像问题

::

    # 默认录像存储位置在jumpserver/data/media  可以通过映射或者软连接方式来使用其他目录

    # 录像存储在 oss，Jumpserver 系统设置-终端设置 录像存储
    {"default": {"TYPE": "server"}, "cn-north-1": {"TYPE": "s3", "BUCKET": "jumpserver", "ACCESS_KEY": "", "SECRET_KEY": "", "REGION": "cn-north-1"}, "ali-oss": {"TYPE": "oss", "BUCKET": "jumpserver", "ACCESS_KEY": "", "SECRET_KEY": "", "ENDPOINT": "http://oss-cn-hangzhou.aliyuncs.com"}}

    # 命令记录保存到 elastic
    {"default": {"TYPE":"server"}, "ali-es": {"TYPE": "elasticsearch", "HOSTS": ["http://elastic:changeme@localhost:9200"]}}

    # 修改后，需要修改在Jumpserver 会话管理-终端管理 修改terminal的配置 录像存储 命令记录

5. 在终端修改管理员密码及新建超级用户

::

    # 管理密码忘记了或者重置管理员密码
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py changepassword  <user_name>

    # 新建超级用户的命令如下命令
    $ python manage.py createsuperuser --username=user --email=user@domain.com

6. 清理celery产生的数据(无法正常推送及连接资产，一直显示........等可以使用，请确定字符集是zh_CN.UTF-8)

::

    # 检测 /etc/locale.conf 是否是 LANG="zh_CN.UTF-8"
    $ cat /etc/locale.conf
    # 如果不是，请修改，注，本例只是以CentOS 7举例，其他的linux请更换路径
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    $ from celery.task.control import discard_all
    $ discard_all()
    $ exit()
    $ cd /opt/jumpserver
    $ ./jms restart celery

    # 如果任然异常，手动结束所有jumpserver进程，然后kill掉未能正常结束的进程，在重新启动jumpserver即可

7. 修改登录超时时间（默认 10 秒）

::

    $ vim /opt/coco/coco/proxy.py
    $ vim /opt/coco/coco/connection.py

    # 把 TIMEOUT = 10 修改成你想要的数字，两个文件都需要修改，单位为：秒
    # TIMEOUT = 10 表示超时时间为10秒，可以自行修改。

8. 升级提示 Table 'xxx' already exists（可用以下命令检查，如果显示内容不一致则无法升级）

::

    $ cd /opt/jumpserver/apps
    $ python manage.py makemigrations
    $ python manage.py migrate --fake
    $ find . | grep migrations | grep apps | grep -v 'pyc' | grep -v '__init__'
    # 把这里的内容和下面数据库查询的内容对比

    # mysql -uroot
    > use jumpserver;
    > select * from django_migrations;
    # 如果对比结果不一样则无法升级
    > quit;

9. 设置浏览器过期

::

    $ vim /opt/jumpserver/apps/jumpserver/settings.py

    # 找到如下行，注释（可参考 django 设置 session 过期时间），修改或者新增你要的设置即可
    # SESSION_COOKIE_AGE = CONFIG.SESSION_COOKIE_AGE or 3600 * 24

    # 如下，设置关闭浏览器 cookie 失效，则修改为
    # SESSION_COOKIE_AGE = CONFIG.SESSION_COOKIE_AGE or 3600 * 24
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
