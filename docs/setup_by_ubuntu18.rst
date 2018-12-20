Ubuntu 18.04 安装文档
--------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  > 开头的行表示需要在 mysql 中执行
-  $ 开头的行表示需要执行的命令

安装过程中遇到问题可参考 `安装过程中常见的问题 <faq_install.html>`_

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.244.144
-  目录: /opt
-  数据库: mariadb
-  代理: nginx

开始安装
~~~~~~~~~~~~

一. 准备 Python3 和 Python 虚拟环境
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1.1 安装依赖包**

.. code-block:: shell

    $ apt-get update && apt-get -y upgrade
    $ apt-get -y install wget gcc libffi-dev git

    # 修改字符集,否则可能报 input/output error的问题,因为日志里打印了中文
    $ apt-get -y install language-pack-zh-hans
    $ export LC_ALL="zh_CN.utf8"
    $ echo 'LANG="zh_CN.utf8"' > /etc/default/locale

**1.2 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke**

.. code-block:: shell

    $ apt-get -y install redis-server

**1.3 安装 MySQL**

本教程使用 Mysql 作为数据库,如果不使用 Mysql 可以跳过相关 Mysql 安装和配置

.. code-block:: shell

    $ apt-get -y install mysql-server libmysqlclient-dev

**1.4 创建数据库 Jumpserver 并授权**

.. code-block:: shell

    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'weakPassword';
    > flush privileges;
    > quit

**1.5 安装 Python3.6**

.. code-block:: shell

    $ apt-get -y install python3.6-dev python3.6-venv

**1.6 建立 Python 虚拟环境**

为了不扰乱原来的环境我们来使用 Python 虚拟环境

.. code-block:: shell

    $ cd /opt
    $ python3.6 -m venv py3
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功,以后运行 Jumpserver 都要先运行以上 source 命令,以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

二. 安装 Jumpserver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**2.1 下载或 Clone 项目**

.. code-block:: shell

    $ cd /opt/
    $ git clone https://github.com/jumpserver/jumpserver.git

**2.2 安装依赖包**

.. code-block:: shell

    $ cd /opt/jumpserver/requirements
    $ apt-get -y install $(cat deb_requirements.txt)

**2.3 安装 Python 库依赖**

.. code-block:: shell

    $ pip install --upgrade pip setuptools
    $ pip install -r requirements.txt

**2.4 修改 Jumpserver 配置文件**

.. code-block:: shell

    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vim config.py

    # 注意对齐,不要直接复制本文档的内容

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

**2.5 运行 Jumpserver**

.. code-block:: shell

    $ cd /opt/jumpserver
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d

    # 新版本更新了运行脚本,使用方式./jms start|stop|status|restart all  后台运行请添加 -d 参数

运行不报错,请继续往下操作

三. 安装 SSH Server 和 WebSocket Server: Coco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**3.1 安装 Docker**

.. code-block:: shell

    $ apt-get -y install apt-transport-https ca-certificates curl software-properties-common
    $ curl -fsSL http://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo apt-key add -
    $ add-apt-repository "deb [arch=amd64] http://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable"
    $ apt-get -y update
    $ apt-get -y install docker-ce
    $ curl -sSL https://get.daocloud.io/daotools/set_mirror.sh | sh -s http://f1361db2.m.daocloud.io
    $ systemctl restart docker.service

**3.2 部署 Coco**

.. code-block:: shell

    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> -e BOOTSTRAP_TOKEN=nwv4RdXpM82LtSvmV jumpserver/jms_coco:1.4.6

    # http://<Jumpserver_url> 指向 jumpserver 的服务端口, 如 http://192.168.244.144:8080
    # BOOTSTRAP_TOKEN 为 Jumpserver/config.py 里面的 BOOTSTRAP_TOKEN

四. 安装 RDP Server 和 VNC Server: Guacamole
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**4.1 部署 Guacamole**

.. code-block:: shell

    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> -e BOOTSTRAP_TOKEN=nwv4RdXpM82LtSvmV jumpserver/jms_guacamole:1.4.6
    # http://<Jumpserver_url> 指向 jumpserver 的服务端口, 如 http://192.168.244.144:8080
    # BOOTSTRAP_TOKEN 为 Jumpserver/config.py 里面的 BOOTSTRAP_TOKEN

五. 安装 Web Terminal 前端: Luna
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

访问(https://github.com/jumpserver/luna/releases)下载对应版本的 release 包,直接解压,不需要编译

**5.1 部署 Luna**

.. code-block:: shell

    $ cd /opt/
    $ wget https://github.com/jumpserver/luna/releases/download/1.4.6/luna.tar.gz
    $ tar xf luna.tar.gz
    $ chown -R root:root luna

六. 配置 Nginx 整合各组件
~~~~~~~~~~~~~~~~~~~~~~~~~

**6.1 安装 Nginx**

.. code-block:: shell

    $ add-apt-repository "deb http://nginx.org/packages/ubuntu/ $(lsb_release -cs) nginx"
    $ curl -fsSL http://nginx.org/keys/nginx_signing.key | sudo apt-key add -
    $ apt-get -y install nginx

**6.2 准备配置文件 /etc/nginx/conf.d/jumpserver.conf**

.. code-block:: nginx

    $ rm -rf /etc/nginx/conf.d/default.conf
    $ vim /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;
        server_name _;

        client_max_body_size 100m;  # 录像及文件上传大小限制

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;
        }

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;
        }

        location /static/ {
            root /opt/jumpserver/data/;
        }

        location /socket.io/ {
            proxy_pass       http://localhost:5000/socket.io/;
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
            proxy_pass       http://localhost:5000/coco/;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /guacamole/ {
            proxy_pass       http://localhost:8081/;
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location / {
            proxy_pass http://localhost:8080;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

    }

**6.3 重启 Nginx**

.. code-block:: shell

    $ nginx -t  # 如果没有报错请继续
    $ systemctl restart nginx

**6.4 开始使用 Jumpserver**

服务全部启动后,访问 http://192.168.244.144

默认账号: admin 密码: admin

到Jumpserver 会话管理-终端管理 检查 Coco Guacamole 等应用的注册

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
