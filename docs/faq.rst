FAQ
==========
.. toctree::
   :maxdepth: 1

   Sftp 使用说明 <faq_sftp.rst>
   Telnet 使用说明 <faq_telnet.rst>
   安装过程 常见问题 <faq_install.rst>
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

    # 找到如下行，注释（可参考 django 设置 session 过期时间），修改你要的设置即可
    # SESSION_COOKIE_AGE = CONFIG.SESSION_COOKIE_AGE or 3600 * 24

    # 如下，设置关闭浏览器 cookie 失效，则修改为
    # SESSION_COOKIE_AGE = CONFIG.SESSION_COOKIE_AGE or 3600 * 24
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

10. MFA遗失无法登陆

::

    # 普通用户联系管理员关闭MFA，登录成功后用户在个人信息里面重新绑定.
    # 如果管理员遗失无法登陆, 修改数据库 user_user 表对应用户的 otp_level 为 0 , 重新登陆绑定即可
    # 如果在系统设置里面开启的 MFA 二次认证 ，需要修改数据库 settings 表 SECURITY_MFA_AUTH 的 value 值为 false

11. 用户管理的用户与资产管理的管理用户、系统用户说明

::

    # 用户管理里面的用户是登录 Jumpserver 使用的，类似 用户使用自己的阿里云账户 登录 阿里云平台
    # 资产管理下面的 管理用户 和 系统用户 都是资产的登录账户，管理用户是 Jumpserver 调用，系统用户是给 普通用户 登录资产使用的账户
    # 管理用户是给 Jumpserver 使用，相当于服务账户，用来检测资产的存活，硬件信息，推送系统用户等，后期还会用来执行命令等
    # 系统用户是给 使用Jumpserver登录资产的人 使用，就像 你 我 一样的人，这个人先要登录 Jumpserver ，然后使用 系统用户 连接资产
    以阿里云例：先登录阿里云平台，看到资产后使用资产上面的账户登录资产。
    Jumpserver：先登录Jumpserver，看到资产后使用系统用户登录资产，一个意思。

12. 资产授权说明

::

    # 资产授权就是把 系统用户关联到用户 并授权到 对应的资产
    # 用户只能看到自己被授权的资产

13. Web Terminal 页面经常需要重新刷新页面才能连接资产

::

    # 具体表现为在luna页面一会可以连接资产，一会就不行，需要多次刷新页面
    # 如果从开发者工具里面看，可以看到部分不正常的 502 socket.io
    # 此问题一般是由最前端一层的nginx反向代理造成的，需要在每层的代理上添加（注意是每层）
    $ vim /etc/nginx/conf.d/jumpserver.conf  # 配置文件所在目录，自行修改

    ...  # 省略

    location /socket.io/ {
                proxy_pass http://你后端的服务器url地址/socket.io/;
                proxy_buffering off;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
                access_log off;  # 不记录到 log
    }
    ...

    # 为了便于理解，附上一份 demo 网站的配置文件参考
    $ vim /etc/nginx/conf.d/jumpserver.conf
    server {

        listen 80;
        server_name demo.jumpserver.org;

        location / {
                # 这里的IP是后端服务器的IP，后端服务器就是文档一步一步安装来的
                proxy_pass http://192.168.244.144;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_read_timeout 150;
        }

        # 新增下面内容
        location /socket.io/ {
                proxy_pass http://192.168.244.144/socket.io/;
                proxy_buffering off;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location /guacamole/ {
                proxy_pass       http://192.168.244.144/guacamole/;
                proxy_buffering off;
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection $http_connection;
                client_max_body_size 100m;  # Windows 文件上传大小限制
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
