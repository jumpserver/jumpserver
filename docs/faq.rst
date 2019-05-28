FAQ
==========
.. toctree::
   :maxdepth: 1

   MFA 使用说明 <faq_mfa.rst>
   LDAP 使用说明 <faq_ldap.rst>
   SFTP 使用说明 <faq_sftp.rst>
   TELNET 使用说明 <faq_telnet.rst>
   Docker 使用说明 <faq_docker.rst>
   Radius 使用说明 <faq_radius.rst>
   安装过程 常见问题 <faq_install.rst>
   升级过程 常见问题 <faq_upgrade.rst>
   Firewalld 使用说明 <faq_firewalld.rst>
   RDP 协议资产连接说明 <faq_rdp.rst>
   SSH 协议资产连接说明 <faq_ssh.rst>
   添加组织 及 组织管理员说明 <faq_org.rst>

其他问题
~~~~~~~~~~~~~~~~~~~~~

1. 用户、系统用户、管理用户的关系

.. code-block:: vim

    # 用户管理里面的用户列表 是用来登录jumpserver平台的用户, 用户需要先登录jumpserver平台, 才能管理或者连接资产
    # 资产管理里面的管理用户 是jumpserver用来管理资产需要的服务账户, Linux资产需要root或 NOPASSWD: ALL sudo
    权限, Jumpserver使用该用户来 '推送系统用户'、'获取资产硬件信息'等。Windows资产随意指定一个, 暂无作用
    # 资产管理里面的系统用户 是jumpserver用户连接资产需要的登录账户, Linux资产可以自动推送该系统用户到资产上,
    Windows需要指定资产上已经创建的系统用户

2. luna 无法访问

.. code-block:: vim

    # 访问 Web终端 提示 Luna是单独部署的一个程序, 请不要通过 8080 端口访问 jumpserver, 通过 nginx 代理端口进行访问
    # 访问 Web终端 提示 403 Forbidden错误, 一般是nginx配置文件的luna路径不正确或者下载了源代码, 请重新下载编译好的代码
    # 访问 Web终端 提示 502 Bad Gateway错误, 一般是selinux和防火墙的问题, 请根据nginx的errorlog来检查

3. 在终端修改管理员密码及新建超级用户

.. code-block:: shell

    # 管理密码忘记了或者重置管理员密码
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py changepassword  <user_name>

    # 新建超级用户的命令如下命令
    $ python manage.py createsuperuser --username=user --email=user@domain.com

    # 登陆提示密码过期可以直接点击忘记密码, 通过邮箱重置; 如果未设置邮箱, 通过以下代码重置
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    > from users.models import User
    > u = User.objects.get(username='admin')  # admin 为你要修改的用户
    > u.reset_password('password')  # password 为你要修改的密码
    > u.save()

4. 修改 SSH 资产登录超时时间(TIMEOUT 默认 10 秒)

.. code-block:: shell

    $ vi /opt/coco/config.yml

    # 把 SSH_TIMEOUT: 15 修改成你想要的数字 单位为：秒
    SSH_TIMEOUT: 60

5. 设置浏览器会话过期

.. code-block:: shell

    $ vi /opt/jumpserver/config.yml

    # 找到如下行(可参考 django 设置 session 过期时间), 修改你要的设置即可
    # SESSION_COOKIE_AGE: 86400
    # SESSION_EXPIRE_AT_BROWSER_CLOSE: false

    # 如下, 设置关闭浏览器 cookie 失效, 则修改为
    # SESSION_COOKIE_AGE: 86400
    SESSION_EXPIRE_AT_BROWSER_CLOSE: true

    # 86400 单位是秒(s)

6. 资产授权说明

.. code-block:: vim

    资产授权就是把 系统用户关联到用户 并授权到 对应的资产
    用户只能看到自己被授权的资产

7. Web Terminal 页面经常需要重新刷新页面才能连接资产

.. code-block:: nginx

    # 具体表现为在luna页面一会可以连接资产, 一会就不行, 需要多次刷新页面
    # 如果从开发者工具里面看, 可以看到部分不正常的 502 socket.io
    # 此问题一般是由最前端一层的nginx反向代理造成的, 需要在每层的代理上添加(注意是每层)
    $ vi /etc/nginx/conf.d/jumpserver.conf  # 配置文件所在目录, 自行修改

    ...  # 省略

    location /socket.io/ {
            proxy_pass http://你后端的服务器url地址/socket.io/;
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;  # 不记录到 log
    }

    location /guacamole/ {
            proxy_pass       http://你后端的服务器url地址/guacamole/;
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;  # 不记录到 log
    }
    ...

    # 为了便于理解, 附上一份 demo 网站的配置文件参考
    $ vi /etc/nginx/conf.d/jumpserver.conf
    server {

        listen 80;
        server_name demo.jumpserver.org;

        client_max_body_size 100m;  # 上传录像大小限制

        location / {
                # 这里的IP是后端服务器的IP, 后端服务器就是文档一步一步安装来的
                proxy_pass http://192.168.244.144;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_read_timeout 150;
        }

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
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }

8. 连接资产时提示 System user <xxx> and asset <xxx> protocol are inconsistent.

.. code-block:: shell

    # 这是因为系统用户的协议和资产的协议不一致导致的
    # 检查系统用户的协议和资产的协议
    # 如果是更新了版本 Windows资产 出现的问题, 请执行下面代码解决
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/utils
    $ sh 2018_07_15_set_win_protocol_to_ssh.sh

    # 如果不存在 2018_07_15_set_win_protocol_to_ssh.sh 脚本, 可以手动执行下面命令解决
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from assets.models import Asset
    >>> Asset.objects.filter(platform__startswith='Win').update(protocol='rdp')
    >>> exit()


9. 重启服务器后无法访问 Jumpserver, 页面提示502 或者 403等

.. code-block:: shell

    # CentOS 7 临时关闭
    $ setenforce 0  # 临时关闭 selinux, 重启后失效
    $ systemctl stop firewalld.service  # 临时关闭防火墙, 重启后失效

    # Centos 7 如需永久关闭, 还需执行下面步骤
    $ sed -i "s/SELINUX=enforcing/SELINUX=disabled/g" /etc/selinux/config  # 禁用 selinux
    $ systemctl disable firewalld.service  # 禁用防火墙

    # Centos 7 在不关闭 selinux 和 防火墙 的情况下使用 Jumpserver
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent  # nginx 端口
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent  # 用户SSH登录端口 coco
      --permanent  永久生效, 没有此参数重启后失效

    $ firewall-cmd --reload  # 重新载入规则

    $ setsebool -P httpd_can_network_connect 1  # 设置 selinux 允许 http 访问


10. 传递明文数据到 Jumpserver 数据库(数据导入)

.. code-block:: shell

    # 以导入 admin 用户 public_key 为例
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from users.models import User
    >>> user = User.objects.get(username='admin')
    >>> user.public_key = '明文key'
    >>> user.save()

11. 登录提示登录频繁

.. code-block:: shell

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/utils
    $ sh unblock_all_user.sh

    # 如果不存在 unblock_all_user.sh 文件
    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from django.core.cache import cache
    >>> cache.delete_pattern('_LOGIN_BLOCK_*')
    >>> cache.delete_pattern('_LOGIN_LIMIT_*')
    >>> exit()
