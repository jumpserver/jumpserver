分布式部署文档 - jumpserver 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.30

+----------+------------+-----------------+---------------+------------------------+
| Protocol | ServerName |        IP       |      Port     |         Used By        |
+==========+============+=================+===============+========================+
|    TCP   | Jumpserver | 192.168.100.30  |    80, 8080   | Nginx, Coco, Guacamole |
+----------+------------+-----------------+---------------+------------------------+

开始安装
~~~~~~~~~~~~

.. code-block:: shell

    # 升级系统
    $ yum upgrade -y

    # 安装依赖包
    $ yum -y install gcc epel-release git

    # 设置防火墙,开放 80 端口给 nginx 访问,开放 8080 端口给 coco 和 guacamole 访问
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.100" port protocol="tcp" port="80" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.40" port protocol="tcp" port="8080" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.50" port protocol="tcp" port="8080" accept"
    $ firewall-cmd --reload

    # 安装 nginx
    $ yum -y install nginx
    $ systemctl enable nginx

    # 安装 Python3.6
    $ yum -y install python36 python36-devel

    # 配置 py3 虚拟环境
    $ python3.6 -m venv /opt/py3
    $ source /opt/py3/bin/activate

    # 下载 Jumpserver
    $ git clone https://github.com/jumpserver/jumpserver.git

    # 安装依赖 RPM 包
    $ yum -y install $(cat /opt/jumpserver/requirements/rpm_requirements.txt)

    # 安装 Python 库依赖
    $ pip install --upgrade pip setuptools
    $ pip install -r /opt/jumpserver/requirements/requirements.txt

    # 修改 jumpserver 配置文件
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

.. code-block:: nginx

    # 修改 nginx 配置文件(如果无法正常访问,请注释掉 nginx.conf 的 server 所有字段)
    $ vi /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;

        client_max_body_size 100m;  # 录像上传大小限制

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;  # 录像位置,如果修改安装目录,此处需要修改
        }

        location /static/ {
            root /opt/jumpserver/data/;  # 静态资源,如果修改安装目录,此处需要修改
        }

        location / {
            proxy_pass http://localhost:8080;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }

.. code-block:: shell

    # nginx 测试并启动,如果报错请按报错提示自行解决
    $ nginx -t
    $ systemctl start nginx

    # 运行 Jumpserver
    $ cd /opt/jumpserver
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d
    # 新版本更新了运行脚本,使用方式./jms start|stop|status all  后台运行请添加 -d 参数

    # 访问 http://192.168.100.30 默认账号: admin 密码: admin

    # 多节点部署,请参考此文档,设置数据库时请选择从库,其他的一样
