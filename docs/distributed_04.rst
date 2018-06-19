分布式部署文档 - jumpserver 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.11

开始安装
~~~~~~~~~~~~

::

    # 升级系统
    $ yum upgrade -y

    # 安装依赖包
    $ yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel epel-release git

    # 安装 redis
    $ yum -y install redis
    $ systemctl enable redis
    $ systemctl start redis

    # 安装 nginx
    $ yum -y install nginx
    $ systemctl enable nginx

    # 安装 Python3.6.1
    $ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
    $ tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1
    $ ./configure && make && make install

    # 配置 py3 虚拟环境
    $ python3 -m venv /opt/py3
    $ source /opt/py3/bin/activate

    # 配置 autoenv
    $ git clone git://github.com/kennethreitz/autoenv.git
    $ echo 'source /opt/autoenv/activate.sh' >> ~/.bashrc
    $ source ~/.bashrc

    # 下载 Jumpserver
    $ git clone --depth=1 https://github.com/jumpserver/jumpserver.git
    $ echo "source /opt/py3/bin/activate" > /opt/jumpserver/.env
    $ cd /opt/jumpserver && git checkout master && git pull
    # 首次进入 jumpserver 文件夹会有提示，按 y 即可
    # Are you sure you want to allow this? (y/N) y

    # 安装依赖 RPM 包
    $ yum -y install $(cat /opt/jumpserver/requirements/rpm_requirements.txt)

    # 安装 Python 库依赖
    $ pip install --upgrade pip && pip install -r /opt/jumpserver/requirements/requirements.txt

    # 修改 jumpserver 配置文件
    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py

    #注意: 配置文件是 Python 格式，不要用 TAB，而要用空格，请手动修改，注意对齐，不要直接复制本文内容

    ...
    class Config:
        # Use it to encrypt or decrypt data

        # Jumpserver 使用 SECRET_KEY 进行加密
        # SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'
        SECRET_KEY = os.environ.get('SECRET_KEY') or '请随意输入随机字符串（推荐字符大于等于 50位）'

        # Django security setting, if your disable debug model, you should setting that
        ALLOWED_HOSTS = ['*']

        # Development env open this, when error occur display the full process track, Production disable it
        # DEBUG 模式 True为开启 False为关闭，默认开启
        DEBUG = False

        # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
        # 日志级别，默认为DEBUG，可调整为INFO, WARNING, ERROR, CRITICAL
        LOG_LEVEL = 'WARNING'
        LOG_DIR = os.path.join(BASE_DIR, 'logs')

        # Database setting, Support sqlite3, mysql, postgres ....
        # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases
        # 使用的数据库配置，支持sqlite3, mysql, postgres等，默认使用sqlite3

        # SQLite setting:
        # 默认使用SQLite，如果使用其他数据库请注释下面两行
        # DB_ENGINE = 'sqlite3'
        # DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')
        # MySQL or postgres setting like:
        # 如果需要使用mysql或postgres，请取消下面的注释并输入正确的信息,本例使用mysql做演示
        DB_ENGINE = 'mysql'
        DB_HOST = '192.168.100.10'
        DB_PORT = 3306
        DB_USER = 'jumpserver'
        DB_PASSWORD = 'somepassword'
        DB_NAME = 'jumpserver'

        # When Django start it will bind this host and port
        # Django 监听的ip和端口，部署代理服务器后应该把0.0.0.0修改成127.0.0.1，这里的意思是允许x.x.x.x访问，127.0.0.1表示仅允许自身访问。
        # ./manage.py runserver 127.0.0.1:8080
        HTTP_BIND_HOST = '127.0.0.1'
        HTTP_LISTEN_PORT = 8080

        # Use Redis as broker for celery and web socket
        # Redis 相关设置
        REDIS_HOST = '127.0.0.1'
        REDIS_PORT = 6379
        REDIS_PASSWORD = ''
        BROKER_URL = 'redis://%(password)s%(host)s:%(port)s/3' % {
            'password': REDIS_PASSWORD,
            'host': REDIS_HOST,
            'port': REDIS_PORT,
        }
    ...

    config = DevelopmentConfig()

::

    # 设置防火墙，开启 80 端口
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent
    $ firewall-cmd --reload

    # 设置 http 访问权限
    $ setsebool -P httpd_can_network_connect 1

    # 修改 nginx 配置文件（如果无法正常访问，请注释掉 nginx.conf 的 server 所有字段）
    $ vim /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;
        }

        location /static/ {
            root /opt/jumpserver/data/;
        }

        location / {
            proxy_pass http://localhost:8080;
        }
    }

::

    # nginx 测试并启动，如果报错请按报错提示自行解决
    $ nginx -t
    $ systemctl start nginx

    # 生成数据库表结构和初始化数据
    $ cd /opt/jumpserver/utils
    $ bash make_migrations.sh

    # 运行 Jumpserver
    $ cd /opt/jumpserver
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d
    # 新版本更新了运行脚本，使用方式./jms start|stop|status all  后台运行请添加 -d 参数

    # 访问 http://192.168.100.11 默认账号: admin 密码: admin
