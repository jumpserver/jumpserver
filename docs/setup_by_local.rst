CentOS 7 组件离线安装文档
--------------------------------------------

说明
~~~~~~~

- 请用新的服务器进行安装
- 本文档适用于网络较差的环境，非完全离线安装（仅提供一些因为网络问题无法下载或者下载慢的组件）
- 安装过程中遇到问题可参考 `安装过程中常见的问题 <faq_install.html>`_

百度云盘：https://pan.baidu.com/s/1FmD-cQp_TsT1OI_U5eFLUw

开始安装
~~~~~~~~~~~~

::

    # 把下载的压缩包上传到要安装的服务器任意目录，然后在该目录执行下面命令
    $ tar xf Python-3.6.1.tar.xz -C /opt
    $ tar xf jumpserver.tar.gz -C /opt
    $ tar xf coco.tar.gz -C /opt
    $ tar xf luna.tar.gz -C /opt
    $ tar xf package.tar.gz -C /opt
    $ tar xf autoenv.tar.gz -C /opt
    $ mv guacamole.tar /opt

    # yum update -y

    # 防火墙 与 selinux 设置说明，如果已经关闭了 防火墙 和 Selinux 的用户请跳过设置
    $ systemctl start firewalld
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent  # Jumpserver 对外端口
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent  # 用户SSH登录端口 coco
      --permanent  永久生效，没有此参数重启后失效

    $ firewall-cmd --reload  # 重新载入规则

    $ setsebool -P httpd_can_network_connect 1  # 设置 selinux 允许 http 访问
    $ mkdir -p /opt/guacamole/key
    $ chcon -Rt svirt_sandbox_file_t /opt/guacamole/key  # 设置 selinux 允许容器对目录读写

    # 修改字符集，否则可能报 input/output error的问题，因为日志里打印了中文
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf

    # 安装依赖包
    $ yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel epel-release git

    # 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke
    $ yum -y install redis
    $ systemctl enable redis
    $ systemctl start redis

    # 安装 MySQL，如果不使用 Mysql 可以跳过相关 Mysql 安装和配置，支持sqlite3, mysql, postgres等
    $ yum -y install mariadb mariadb-devel mariadb-server # centos7下叫mariadb，用法与mysql一致
    $ systemctl enable mariadb
    $ systemctl start mariadb
    # 创建数据库 Jumpserver 并授权
    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'weakPassword';
    > flush privileges;

    # 安装 Nginx ，用作代理服务器整合 Jumpserver 与各个组件
    $ yum -y install nginx
    $ systemctl enable nginx

    # 编译 Python3.6.1
    $ cd /opt/Python-3.6.1
    $ ./configure && make && make install

    # 配置并载入 Python3 虚拟环境
    $ cd /opt
    $ python3 -m venv py3  # py3 为虚拟环境名称，可自定义
    $ source /opt/py3/bin/activate  # 退出虚拟环境可以使用 deactivate 命令

    # 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，载入环境后默认以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 自动载入 Python3 虚拟环境
    $ cd /opt
    $ echo 'source /opt/autoenv/activate.sh' >> ~/.bashrc
    $ source ~/.bashrc

    # 升级 Jumpserver 与 Coco
    $ cd /opt/jumpserver && git checkout master && git pull
    $ echo "source /opt/py3/bin/activate" > /opt/jumpserver/.env  # 进入 jumpserver 目录时将自动载入 python 虚拟环境

    $ cd /opt/coco && git checkout master && git pull
    $ echo "source /opt/py3/bin/activate" > /opt/coco/.env  # 进入 coco 目录时将自动载入 python 虚拟环境

    # 安装依赖 RPM 包
    $ yum -y install $(cat /opt/jumpserver/requirements/rpm_requirements.txt)
    $ yum -y install $(cat /opt/coco/requirements/rpm_requirements.txt)

    # 安装 Python 库依赖
    $ pip install --no-index --find-links="/opt/package/" --upgrade pip
    $ pip install -r /opt/jumpserver/requirements/requirements.txt --no-index --find-links="/opt/package/jumpserver/"
    $ pip install -r /opt/coco/requirements/requirements.txt --no-index --find-links="/opt/package/coco/"

::


    # 修改 Jumpserver 配置文件
    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py

    # 注意对齐，不要直接复制本文档的内容，实际内容以文件为准，本文仅供参考

**注意: 配置文件是 Python 格式，不要用 TAB，而要用空格**

::

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
        # Use it to encrypt or decrypt data

        # Jumpserver 使用 SECRET_KEY 进行加密，请务必修改以下设置
        # SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'
        SECRET_KEY = '请随意输入随机字符串（推荐字符大于等于 50位）'

        # Django security setting, if your disable debug model, you should setting that
        ALLOWED_HOSTS = ['*']

        # DEBUG 模式 True为开启 False为关闭，默认开启，生产环境推荐关闭
        # 注意：如果设置了DEBUG = False，访问8080端口页面会显示不正常，需要搭建 nginx 代理才可以正常访问
        DEBUG = os.environ.get("DEBUG") or False

        # 日志级别，默认为DEBUG，可调整为INFO, WARNING, ERROR, CRITICAL，默认INFO
        LOG_LEVEL = os.environ.get("LOG_LEVEL") or 'WARNING'
        LOG_DIR = os.path.join(BASE_DIR, 'logs')

        # 使用的数据库配置，支持sqlite3, mysql, postgres等，默认使用sqlite3
        # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases

        # 默认使用SQLite3，如果使用其他数据库请注释下面两行
        # DB_ENGINE = 'sqlite3'
        # DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')

        # 如果需要使用mysql或postgres，请取消下面的注释并输入正确的信息,本例使用mysql做演示(mariadb也是mysql)
        DB_ENGINE = os.environ.get("DB_ENGINE") or 'mysql'
        DB_HOST = os.environ.get("DB_HOST") or '127.0.0.1'
        DB_PORT = os.environ.get("DB_PORT") or 3306
        DB_USER = os.environ.get("DB_USER") or 'jumpserver'
        DB_PASSWORD = os.environ.get("DB_PASSWORD") or 'weakPassword'
        DB_NAME = os.environ.get("DB_NAME") or 'jumpserver'

        # Django 监听的ip和端口，生产环境推荐把0.0.0.0修改成127.0.0.1，这里的意思是允许x.x.x.x访问，127.0.0.1表示仅允许自身访问
        # ./manage.py runserver 127.0.0.1:8080
        HTTP_BIND_HOST = '127.0.0.1'
        HTTP_LISTEN_PORT = 8080

        # Redis 相关设置
        REDIS_HOST = os.environ.get("REDIS_HOST") or '127.0.0.1'
        REDIS_PORT = os.environ.get("REDIS_PORT") or 6379
        REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD") or ''
        REDIS_DB_CELERY = os.environ.get('REDIS_DB') or 3
        REDIS_DB_CACHE = os.environ.get('REDIS_DB') or 4

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

::


    # 修改 Coco 配置文件
    $ cd /opt/coco
    $ mkdir keys
    $ cp conf_example.py conf.py
    $ vi conf.py

    # 注意对齐，不要直接复制本文档的内容

**注意: 配置文件是 Python 格式，不要用 TAB，而要用空格**

::

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
        NAME = "coco"

        # Jumpserver项目的url, api请求注册会使用, 如果Jumpserver没有运行在127.0.0.1:8080，请修改此处
        # CORE_HOST = os.environ.get("CORE_HOST") or 'http://127.0.0.1:8080'
        CORE_HOST = 'http://127.0.0.1:8080'

        # 启动时绑定的ip, 默认 0.0.0.0
        # BIND_HOST = '0.0.0.0'

        # 监听的SSH端口号, 默认2222
        # SSHD_PORT = 2222

        # 监听的HTTP/WS端口号，默认5000
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
        LOG_LEVEL = 'WARN'

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

        # SSH黑名单, 如果用户同时在白名单和黑名单，黑名单优先生效
        # BLOCK_SSH_USER = []

        # 和Jumpserver 保持心跳时间间隔
        # HEARTBEAT_INTERVAL = 5

        # Admin的名字，出问题会提示给用户
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

::


    # 配置 Web Terminal 前端: Luna  需要 Nginx 来运行访问
    $ cd /opt
    $ chown -R root:root luna

    # 安装 Windows 支持组件
    $ yum remove docker-latest-logrotate docker-logrotate docker-selinux dockdocker-engine
    $ yum install -y yum-utils device-mapper-persistent-data lvm2

    # 国外使用 docker 官方源
    $ yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

    # 国内请使用阿里云镜像源
    $ yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    $ rpm --import http://mirrors.aliyun.com/docker-ce/linux/centos/gpg

    $ yum makecache fast
    $ yum install docker-ce
    $ systemctl enable docker
    $ systemctl start docker
    $ docker load < /opt/guacamole.tar

::


    # 配置 Nginx 整合各组件
    $ vim /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;
        server_name demo.jumpserver.org;  # 修改成你的域名

        client_max_body_size 100m;  # 录像及文件上传大小限制

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;  # luna 路径，如果修改安装目录，此处需要修改
        }

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;  # 录像位置，如果修改安装目录，此处需要修改
        }

        location /static/ {
            root /opt/jumpserver/data/;  # 静态资源，如果修改安装目录，此处需要修改
        }

        location /socket.io/ {
            proxy_pass       http://localhost:5000/socket.io/;  # 如果coco安装在别的服务器, 请填写它的ip
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
            proxy_pass       http://localhost:8081/;  # 如果docker安装在别的服务器, 请填写它的ip
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
            proxy_pass http://localhost:8080;  # 如果jumpserver安装在别的服务器, 请填写它的ip
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }

::


    # 生成数据库表结构和初始化数据
    $ cd /opt/jumpserver/utils
    $ bash make_migrations.sh

    # 运行 Jumpserver
    $ cd /opt/jumpserver
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d
    # 新版本更新了运行脚本，使用方式./jms start|stop|status|restart all  后台运行请添加 -d 参数

    # 运行 Coco
    $ cd /opt/coco
    $ cp conf_example.py conf.py
    $ ./cocod start  # 后台运行使用 -d 参数./cocod start -d
    # 新版本更新了运行脚本，使用方式./cocod start|stop|status|restart  后台运行请添加 -d 参数

    # 运行 Guacamole
    # 注意：这里需要修改下 http://<填写jumpserver的url地址> 例: http://192.168.244.144 不能使用 127.0.0.1
    $ docker run --name jms_guacamole -d \
        -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
        -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
        -e JUMPSERVER_SERVER=http://<填写jumpserver的url地址> \
        jumpserver/guacamole:latest
    # docker 重启容器的方法docker restart jms_guacamole

    # 运行 Nginx
    $ nginx -t   # 确保配置没有问题, 有问题请先解决
    $ systemctl start nginx

    # 访问 http://192.168.244.144 (注意，没有 :8080，通过 nginx 代理端口进行访问)
    # 默认账号: admin 密码: admin  到会话管理-终端管理 接受 Coco Guacamole 等应用的注册
    # 测试连接
    $ ssh -p2222 admin@192.168.244.144
    $ sftp -P2222 admin@192.168.244.144
      密码: admin

    # 如果是用在 Windows 下，Xshell Terminal 登录语法如下
    $ ssh admin@192.168.244.144 2222
    $ sftp admin@192.168.244.144 2222
      密码: admin
      如果能登陆代表部署成功

    # sftp默认上传的位置在资产的 /tmp 目录下
    # windows拖拽上传的位置在资产的 Guacamole RDP上的 G 目录下

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
