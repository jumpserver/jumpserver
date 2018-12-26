一步一步安装(CentOS)
--------------------------

本文档旨在帮助用户了解各组件之间的关系, 生产环境部署建议参考 `进阶安装文档 <quickinstall.html>`_

安装过程中遇到问题可参考 `安装过程中常见的问题 <faq_install.html>`_

测试推荐环境
~~~~~~~~~~~~~

-  CPU: 64位双核处理器
-  内存: 4G DDR3
-  数据库：mysql 版本大于等于 5.6  mariadb 版本大于等于 5.5.6

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.244.144
-  设置 selinux 和防火墙

.. code-block:: shell

    $ firewall-cmd --zone=public --add-port=80/tcp --permanent  # nginx 端口
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent  # 用户SSH登录端口 coco

    $ firewall-cmd --reload  # 重新载入规则

    $ setenforce 0
    $ sed -i "s/enforcing/disabled/g" `grep enforcing -rl /etc/selinux/config`

    # 修改字符集,否则可能报 input/output error的问题,因为日志里打印了中文
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf

一. 准备 Python3 和 Python 虚拟环境
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1.1 安装依赖包**

.. code-block:: shell

    $ yum -y install wget gcc epel-release git

**1.2 安装 Python3.6**

::

    $ yum -y install python36 python36-devel

**1.3 建立 Python 虚拟环境**

因为 CentOS 7 自带的是 Python2,而 Yum 等工具依赖原来的 Python,为了不扰乱原来的环境我们来使用 Python 虚拟环境

.. code-block:: shell

    $ cd /opt
    $ python3.6 -m venv py3
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功,以后运行 Jumpserver 都要先运行以上 source 命令,以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

**1.4 自动载入 Python 虚拟环境配置**

此项仅为懒癌晚期的人员使用,防止运行 Jumpserver 时忘记载入 Python 虚拟环境导致程序无法运行。使用autoenv

.. code-block:: shell

    $ cd /opt
    $ git clone https://github.com/kennethreitz/autoenv.git
    $ echo 'source /opt/autoenv/activate.sh' >> ~/.bashrc
    $ source ~/.bashrc

二. 安装 Jumpserver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**2.1 下载或 Clone 项目**

项目提交较多 git clone 时较大,你可以选择去 Github 项目页面直接下载zip包。

.. code-block:: shell

    $ cd /opt/
    $ git clone https://github.com/jumpserver/jumpserver.git
    $ echo "source /opt/py3/bin/activate" > /opt/jumpserver/.env  # 进入 jumpserver 目录时将自动载入 python 虚拟环境

    # 首次进入 jumpserver 文件夹会有提示,按 y 即可
    # Are you sure you want to allow this? (y/N) y

**2.2 安装依赖 RPM 包**

.. code-block:: shell

    $ cd /opt/jumpserver/requirements
    $ yum -y install $(cat rpm_requirements.txt)  # 如果没有任何报错请继续

**2.3 安装 Python 库依赖**

.. code-block:: shell

    $ pip install --upgrade pip setuptools
    $ pip install -r requirements.txt

**2.4 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke**

.. code-block:: shell

    $ yum -y install redis
    $ systemctl enable redis
    $ systemctl start redis

**2.5 安装 MySQL**

本教程使用 Mysql 作为数据库,如果不使用 Mysql 可以跳过相关 Mysql 安装和配置

.. code-block:: shell

    $ yum -y install mariadb mariadb-devel mariadb-server # centos7下安装的是mariadb
    $ systemctl enable mariadb
    $ systemctl start mariadb

**2.6 创建数据库 Jumpserver 并授权**

.. code-block:: shell

    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'weakPassword';
    > flush privileges;
    > quit

**2.7 修改 Jumpserver 配置文件**

.. code-block:: shell

    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py

    # 注意对齐,不要直接复制本文档的内容,实际内容以文件为准,本文仅供参考

**注意: 配置文件是 Python 格式,不要用 TAB,而要用空格**

.. code-block:: python

    """
        jumpserver.config
        ~~~~~~~~~~~~~~~~~

        Jumpserver project setting file

        :copyright: (c) 2014-2017 by Jumpserver Team
        :license: GPL v2, see LICENSE for more details.
    """
    import os

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


    class Config:
        """
        Jumpserver Config File
        Jumpserver 配置文件

        Jumpserver use this config for drive django framework running,
        You can set is value or set the same envirment value,
        Jumpserver look for config order: file => env => default

        Jumpserver使用配置来驱动Django框架的运行，
        你可以在该文件中设置，或者设置同样名称的环境变量,
        Jumpserver使用配置的顺序: 文件 => 环境变量 => 默认值
        """
        # SECURITY WARNING: keep the secret key used in production secret!
        # 加密秘钥 生产环境中请修改为随机字符串，请勿外泄
        SECRET_KEY = '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'

        # Django security setting, if your disable debug model, you should setting that
        ALLOWED_HOSTS = ['*']

        # SECURITY WARNING: keep the bootstrap token used in production secret!
        # 预共享Token coco和guacamole用来注册服务账号，不在使用原来的注册接受机制
        BOOTSTRAP_TOKEN = 'nwv4RdXpM82LtSvmV'

        # Development env open this, when error occur display the full process track, Production disable it
        # DEBUG 模式 开启DEBUG后遇到错误时可以看到更多日志
        # DEBUG = True
        DEBUG = False

        # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
        # 日志级别
        # LOG_LEVEL = 'DEBUG'
        # LOG_DIR = os.path.join(BASE_DIR, 'logs')
        LOG_LEVEL = 'ERROR'
        LOG_DIR = os.path.join(BASE_DIR, 'logs')

        # Session expiration setting, Default 24 hour, Also set expired on on browser close
        # 浏览器Session过期时间，默认24小时, 也可以设置浏览器关闭则过期
        # SESSION_COOKIE_AGE = 3600 * 24
        # SESSION_EXPIRE_AT_BROWSER_CLOSE = False
        SESSION_EXPIRE_AT_BROWSER_CLOSE = True

        # Database setting, Support sqlite3, mysql, postgres ....
        # 数据库设置
        # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases

        # SQLite setting:
        # 使用单文件sqlite数据库
        # DB_ENGINE = 'sqlite3'
        # DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')

        # MySQL or postgres setting like:
        # 使用Mysql作为数据库
        DB_ENGINE = 'mysql'
        DB_HOST = '127.0.0.1'
        DB_PORT = 3306
        DB_USER = 'jumpserver'
        DB_PASSWORD = 'weakPassword'
        DB_NAME = 'jumpserver'

        # When Django start it will bind this host and port
        # ./manage.py runserver 127.0.0.1:8080
        # 运行时绑定端口
        HTTP_BIND_HOST = '0.0.0.0'
        HTTP_LISTEN_PORT = 8080

        # Use Redis as broker for celery and web socket
        # Redis配置
        REDIS_HOST = '127.0.0.1'
        REDIS_PORT = 6379
        # REDIS_PASSWORD = ''
        # REDIS_DB_CELERY_BROKER = 3
        # REDIS_DB_CACHE = 4

        # Use OpenID authorization
        # 使用OpenID 来进行认证设置
        # BASE_SITE_URL = 'http://localhost:8080'
        # AUTH_OPENID = False  # True or False
        # AUTH_OPENID_SERVER_URL = 'https://openid-auth-server.com/'
        # AUTH_OPENID_REALM_NAME = 'realm-name'
        # AUTH_OPENID_CLIENT_ID = 'client-id'
        # AUTH_OPENID_CLIENT_SECRET = 'client-secret'

        def __init__(self):
            pass

        def __getattr__(self, item):
            return None


    class DevelopmentConfig(Config):
        pass


    class TestConfig(Config):
        pass


    class ProductionConfig(Config):
        pass


    # Default using Config settings, you can write if/else for different env
    config = DevelopmentConfig()

**2.8 运行 Jumpserver**

.. code-block:: shell

    $ cd /opt/jumpserver
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d

    # 新版本更新了运行脚本,使用方式./jms start|stop|status|restart all  后台运行请添加 -d 参数

运行不报错, 请继续往下操作

三. 安装 SSH Server 和 WebSocket Server: Coco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**3.1 下载或 Clone 项目**

新开一个终端,别忘了 source /opt/py3/bin/activate

.. code-block:: shell

    $ cd /opt
    $ source /opt/py3/bin/activate
    $ git clone https://github.com/jumpserver/coco.git
    $ echo "source /opt/py3/bin/activate" > /opt/coco/.env  # 进入 coco 目录时将自动载入 python 虚拟环境

    # 首次进入 coco 文件夹会有提示,按 y 即可
    # Are you sure you want to allow this? (y/N) y

**3.2 安装依赖**

.. code-block:: shell

    $ cd /opt/coco/requirements
    $ yum -y  install $(cat rpm_requirements.txt)
    $ pip install -r requirements.txt

**3.3 修改配置文件并运行**

.. code-block:: shell

    $ cd /opt/coco
    $ mkdir keys logs
    $ cp conf_example.py conf.py  # 如果 coco 与 jumpserver 分开部署,请手动修改 conf.py
    $ vi conf.py

    # 注意对齐,不要直接复制本文档的内容

**注意: 配置文件是 Python 格式,不要用 TAB,而要用空格**

.. code-block:: python

    #!/usr/bin/env python3
    # -*- coding: utf-8 -*-
    #

    import os

    BASE_DIR = os.path.dirname(__file__)


    class Config:
        """
        Coco config file, coco also load config from server update setting below
        """
        # 项目名称, 会用来向Jumpserver注册, 识别而已, 不能重复
        # NAME = "localhost"

        # Jumpserver项目的url, api请求注册会使用, 如果Jumpserver没有运行在127.0.0.1:8080,请修改此处
        # CORE_HOST = os.environ.get("CORE_HOST") or 'http://127.0.0.1:8080'
        CORE_HOST = 'http://127.0.0.1:8080'

        # Bootstrap Token, 预共享秘钥, 用来注册coco使用的service account和terminal
        # 请和jumpserver 配置文件中保持一致，注册完成后可以删除
        # BOOTSTRAP_TOKEN = "PleaseChangeMe"
        BOOTSTRAP_TOKEN = "nwv4RdXpM82LtSvmV"

        # 启动时绑定的ip, 默认 0.0.0.0
        # BIND_HOST = '0.0.0.0'

        # 监听的SSH端口号, 默认2222
        # SSHD_PORT = 2222

        # 监听的HTTP/WS端口号,默认5000
        # HTTPD_PORT = 5000

        # 项目使用的ACCESS KEY, 默认会注册,并保存到 ACCESS_KEY_STORE中,
        # 如果有需求, 可以写到配置文件中, 格式 access_key_id:access_key_secret
        # ACCESS_KEY = None

        # ACCESS KEY 保存的地址, 默认注册后会保存到该文件中
        # ACCESS_KEY_STORE = os.path.join(BASE_DIR, 'keys', '.access_key')

        # 加密密钥
        # SECRET_KEY = None

        # 设置日志级别 ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL', 'CRITICAL']
        # LOG_LEVEL = 'INFO'
        LOG_LEVEL = 'ERROR'

        # 日志存放的目录
        # LOG_DIR = os.path.join(BASE_DIR, 'logs')

        # Session录像存放目录
        # SESSION_DIR = os.path.join(BASE_DIR, 'sessions')

        # 资产显示排序方式, ['ip', 'hostname']
        # ASSET_LIST_SORT_BY = 'ip'

        # 登录是否支持密码认证
        # PASSWORD_AUTH = True

        # 登录是否支持秘钥认证
        # PUBLIC_KEY_AUTH = True

        # SSH白名单
        # ALLOW_SSH_USER = 'all'  # ['test', 'test2']

        # SSH黑名单, 如果用户同时在白名单和黑名单,黑名单优先生效
        # BLOCK_SSH_USER = []

        # 和Jumpserver 保持心跳时间间隔
        # HEARTBEAT_INTERVAL = 5

        # Admin的名字,出问题会提示给用户
        # ADMINS = ''
        COMMAND_STORAGE = {
            "TYPE": "server"
        }
        REPLAY_STORAGE = {
            "TYPE": "server"
        }

        # SSH连接超时时间 (default 15 seconds)
        # SSH_TIMEOUT = 15

        # 语言 = en
        LANGUAGE_CODE = 'zh'


    config = Config()

.. code-block:: shell

    $ ./cocod start  # 后台运行使用 -d 参数./cocod start -d

    # 新版本更新了运行脚本,使用方式./cocod start|stop|status|restart  后台运行请添加 -d 参数

四. 安装 Web Terminal 前端: Luna
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Luna 已改为纯前端,需要 Nginx 来运行访问

访问(https://github.com/jumpserver/luna/releases)下载对应版本的 release 包,直接解压,不需要编译

**4.1 解压 Luna**

.. code-block:: shell

    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.4.6/luna.tar.gz
    $ tar xf luna.tar.gz
    $ chown -R root:root luna

五. 安装 Windows 支持组件(如果不需要管理 windows 资产,可以直接跳过这一步)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Guacamole 需要 Tomcat 来运行

**5.1 安装依赖**

.. code-block:: shell

    $ mkdir /usr/local/lib/freerdp/
    $ ln -s /usr/local/lib/freerdp /usr/lib64/freerdp
    $ rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
    $ rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm
    $ yum -y localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-7.noarch.rpm

    $ yum install -y java-1.8.0-openjdk libtool
    $ yum install -y cairo-devel libjpeg-turbo-devel libpng-devel uuid-devel
    $ yum install -y ffmpeg-devel freerdp-devel freerdp-plugins pango-devel libssh2-devel libtelnet-devel libvncserver-devel pulseaudio-libs-devel openssl-devel libvorbis-devel libwebp-devel ghostscript

**5.2 编译安装 guacamole 服务**

.. code-block:: shell

    $ cd /opt
    $ git clone https://github.com/jumpserver/docker-guacamole.git
    $ cd /opt/docker-guacamole/
    $ tar -xf guacamole-server-0.9.14.tar.gz
    $ cd guacamole-server-0.9.14
    $ autoreconf -fi
    $ ./configure --with-init-dir=/etc/init.d
    $ make && make install
    $ cd ..
    $ rm -rf guacamole-server-0.9.14
    $ ldconfig

**5.3 配置 Tomcat**

.. code-block:: shell

    $ mkdir -p /config/guacamole /config/guacamole/lib /config/guacamole/extensions  # 创建 guacamole 目录
    $ cp /opt/docker-guacamole/guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar
    $ cp /opt/docker-guacamole/root/app/guacamole/guacamole.properties /config/guacamole/  # guacamole 配置文件

    $ cd /config
    $ wget http://mirror.bit.edu.cn/apache/tomcat/tomcat-8/v8.5.35/bin/apache-tomcat-8.5.35.tar.gz
    $ tar xf apache-tomcat-8.5.35.tar.gz
    $ rm -rf apache-tomcat-8.5.35.tar.gz
    $ mv apache-tomcat-8.5.35 tomcat8
    $ rm -rf /config/tomcat8/webapps/*
    $ cp /opt/docker-guacamole/guacamole-0.9.14.war /config/tomcat8/webapps/ROOT.war  # guacamole client
    $ sed -i 's/Connector port="8080"/Connector port="8081"/g' `grep 'Connector port="8080"' -rl /config/tomcat8/conf/server.xml`  # 修改默认端口为 8081
    $ sed -i 's/FINE/WARNING/g' `grep 'FINE' -rl /config/tomcat8/conf/logging.properties`  # 修改 log 等级为 WARNING

    $ cd /config
    $ wget https://github.com/ibuler/ssh-forward/releases/download/v0.0.5/linux-amd64.tar.gz
    $ tar xf linux-amd64.tar.gz -C /bin/
    $ chmod +x /bin/ssh-forward

**5.4 配置环境变量**

.. code-block:: shell

    $ export JUMPSERVER_SERVER=http://127.0.0.1:8080  # http://127.0.0.1:8080 指 jumpserver 访问地址
    $ echo "export JUMPSERVER_SERVER=http://127.0.0.1:8080" >> ~/.bashrc

    # BOOTSTRAP_TOKEN 为 Jumpserver/config.py 里面的 BOOTSTRAP_TOKEN
    $ export BOOTSTRAP_TOKEN=nwv4RdXpM82LtSvmV
    $ echo "export BOOTSTRAP_TOKEN=nwv4RdXpM82LtSvmV" >> ~/.bashrc
    $ export JUMPSERVER_KEY_DIR=/config/guacamole/keys
    $ echo "export JUMPSERVER_KEY_DIR=/config/guacamole/keys" >> ~/.bashrc
    $ export GUACAMOLE_HOME=/config/guacamole
    $ echo "export GUACAMOLE_HOME=/config/guacamole" >> ~/.bashrc

**5.5 启动 Guacamole**

.. code-block:: shell

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

六. 配置 Nginx 整合各组件
~~~~~~~~~~~~~~~~~~~~~~~~~

**6.1 安装 Nginx**

.. code-block:: shell

    $ vi /etc/yum.repos.d/nginx.repo

    [nginx]
    name=nginx repo
    baseurl=http://nginx.org/packages/centos/7/$basearch/
    gpgcheck=0
    enabled=1

    $ yum install -y nginx
    $ rm -rf /etc/nginx/conf.d/default.conf
    $ systemctl enable nginx

**6.3 准备配置文件 修改 /etc/nginx/conf.d/jumpserver.conf**

.. code-block:: nginx

    $ vi /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;  # 代理端口,以后将通过此端口进行访问,不再通过8080端口
        # server_name demo.jumpserver.org;  # 修改成你的域名或者注释掉

        client_max_body_size 100m;  # 录像及文件上传大小限制

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;  # luna 路径,如果修改安装目录,此处需要修改
        }

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;  # 录像位置,如果修改安装目录,此处需要修改
        }

        location /static/ {
            root /opt/jumpserver/data/;  # 静态资源,如果修改安装目录,此处需要修改
        }

        location /socket.io/ {
            proxy_pass       http://localhost:5000/socket.io/;  # 如果coco安装在别的服务器,请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /coco/ {
            proxy_pass       http://localhost:5000/coco/;  # 如果coco安装在别的服务器,请填写它的ip
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /guacamole/ {
            proxy_pass       http://localhost:8081/;  # 如果guacamole安装在别的服务器,请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location / {
            proxy_pass http://localhost:8080;  # 如果jumpserver安装在别的服务器,请填写它的ip
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }

**6.3 运行 Nginx**

.. code-block:: shell

    nginx -t   # 确保配置没有问题, 有问题请先解决

    # CentOS 7
    $ systemctl start nginx
    $ systemctl enable nginx

**6.4 开始使用 Jumpserver**

检查应用是否已经正常运行

服务全部启动后,访问 http://192.168.244.144,访问nginx代理的端口,不要再通过8080端口访问

默认账号: admin 密码: admin

到Jumpserver 会话管理-终端管理 检查 Coco Guacamole 等应用的注册。

**测试连接**

.. code-block:: shell

    如果登录客户端是 macOS 或 Linux ,登录语法如下
    $ ssh -p2222 admin@192.168.244.144
    $ sftp -P2222 admin@192.168.244.144
    密码: admin

    如果登录客户端是 Windows ,Xshell Terminal 登录语法如下
    $ ssh admin@192.168.244.144 2222
    $ sftp admin@192.168.244.144 2222
    密码: admin
    如果能登陆代表部署成功

    # sftp默认上传的位置在资产的 /tmp 目录下
    # windows拖拽上传的位置在资产的 Guacamole RDP上的 G 目录下

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
