CentOS 7 安装文档
--------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  > 开头的行表示需要在 mysql 中执行
-  $ 开头的行表示需要执行的命令

本文档适用于有一定web运维经验的管理员或者工程师，文中不会对安装的软件做过多的解释，仅对需要执行的内容注部分注释，更详细的内容请参考一步一步安装。

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.244.144
-  目录: /opt
-  数据库: mariadb
-  代理: nginx

开始安装
~~~~~~~~~~~~

::


    # 关闭 selinux 与 防火墙 仅为了能正常安装，安装完成后需要配置并重新打开
    $ setenforce 0  # 临时关闭 selinux
    $ systemctl stop iptables.service
    $ systemctl stop firewalld.service

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
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'somepassword';
    > flush privileges;

    # 安装 Nginx ，用作代理服务器整合 Jumpserver 与各个组件
    $ yum -y install nginx
    $ systemctl enable nginx

    # 下载编译 Python3.6.1
    $ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
    $ tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1
    $ ./configure && make && make install

    # 配置并载入 Python3 虚拟环境
    $ cd /opt
    $ python3 -m venv py3  # py3 为虚拟环境名称，可自定义
    $ source /opt/py3/bin/activate  # 退出虚拟环境可以使用 deactivate 命令

    # 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，载入环境后默认以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 自动载入 Python3 虚拟环境
    $ git clone git://github.com/kennethreitz/autoenv.git ~/.autoenv
    $ echo 'source ~/.autoenv/activate.sh' >> ~/.bashrc
    $ source ~/.bashrc

    # 下载 Jumpserver 与 Coco
    $ cd /opt/
    $ git clone https://github.com/jumpserver/jumpserver.git && cd jumpserver && git checkout master && git pull
    $ echo "source /opt/py3/bin/activate" > /opt/jumpserver/.env  # 进入 jumpserver 目录时将自动载入 python 虚拟环境
    $ git clone https://github.com/jumpserver/coco.git && cd coco && git checkout master && git pull
    $ echo "source /opt/py3/bin/activate" > /opt/coco/.env  # 进入 coco 目录时将自动载入 python 虚拟环境

    # 安装依赖 RPM 包
    $ yum -y install $(cat /opt/jumpserver/requirements/rpm_requirements.txt)
    $ yum -y install $(cat /opt/coco/requirements/rpm_requirements.txt)

    # 安装 Python 库依赖
    $ pip install --upgrade pip
    $ pip install -r /opt/jumpserver/requirements/requirements.txt
    $ pip install -r /opt/coco/requirements/requirements.txt

::


    # 修改 Jumpserver 配置文件
    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py

    #注意: 配置文件是 Python 格式，不要用 TAB，而要用空格，请手动修改，注意对齐，不要直接复制本文内容

    ...
    class Config:
        # Use it to encrypt or decrypt data
        # SECURITY WARNING: keep the secret key used in production secret!
        SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'

        # Django security setting, if your disable debug model, you should setting that
        ALLOWED_HOSTS = ['*']

        # Development env open this, when error occur display the full process track, Production disable it
        # DEBUG 模式 True为开启 False为关闭，默认开启
        DEBUG = True

        # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
        # 日志级别，默认为DEBUG，可调整为INFO, WARNING, ERROR, CRITICAL
        LOG_LEVEL = 'DEBUG'
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
        DB_HOST = '127.0.0.1'
        DB_PORT = 3306
        DB_USER = 'root'
        DB_PASSWORD = 'somepassword'
        DB_NAME = 'jumpserver'

        # When Django start it will bind this host and port
        # Django 运行的端口和容器，部署代理服务器后应该把0.0.0.0修改成127.0.0.1，这里的意思是允许x.x.x.x访问，127.0.0.1表示仅允许自身访问。
        # ./manage.py runserver 127.0.0.1:8080
        HTTP_BIND_HOST = '0.0.0.0'
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


    # 修改 Coco 配置文件
    $ cd /opt/coco
    $ cp conf_example.py conf.py
    $ vi conf.py

    #注意: 配置文件是 Python 格式，不要用 TAB，而要用空格，请手动修改，注意对其，不要直接复制本文内容

    ...
    class Config:
    """
    Coco config file, coco also load config from server update setting below
    """
        # 项目名称, 会用来向Jumpserver注册, 识别而已, 不能重复
        # NAME = "localhost"

        # Jumpserver项目的url, api请求注册会使用
        # CORE_HOST = os.environ.get("CORE_HOST") or 'http://127.0.0.1:8080'

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


        config = Config()

::


    # 安装 Web Terminal 前端: Luna  需要 Nginx 来运行访问 访问（https://github.com/jumpserver/luna/releases）下载对应版本的 release 包，直接解压，不需要编译
    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.3.0/dist.tar.gz
    $ tar xvf dist.tar.gz
    $ mv dist luna

    # 安装 Windows 支持组件（如果不需要管理 windows 资产，可以直接跳过这一步）
    $ yum remove docker-latest-logrotate  docker-logrotate  docker-selinux dockdocker-engine
    $ yum install -y yum-utils   device-mapper-persistent-data   lvm2
    $ yum-config-manager     --add-repo     https://download.docker.com/linux/centos/docker-ce.repo
    $ yum makecache fast
    $ yum install docker-ce
    $ systemctl start docker
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写jumpserver的url地址> \
      registry.jumpserver.org/public/guacamole:latest

::


    # 配置 Nginx 整合各组件
    $ vim /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

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
            proxy_pass       http://localhost:5000/socket.io/;  # 如果coco安装在别的服务器，请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /guacamole/ {
            proxy_pass       http://localhost:8081/;  # 如果docker安装在别的服务器，请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
        }

        location / {
            proxy_pass http://localhost:8080;  # 如果jumpserver安装在别的服务器，请填写它的ip
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

    # 运行 Nginx
    $ nginx -t   # 确保配置没有问题, 有问题请先解决
    $ systemctl start nginx

    # 访问 http://192.168.244.144 默认账号: admin 密码: admin  到会话管理-终端管理 接受 Coco Guacamole 等应用的注册
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

    # 其他的ssh及sftp客户端这里就不多做说明，自行搜索使用

    # 防火墙 与 selinux 设置说明
    $ systemctl start firewalld
    $ firewall-cmd --zone=public --add-port=8080/tcp --permanent  # jumpserver 端口
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent  # nginx 端口
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent  # 用户SSH登录端口 coco
    $ firewall-cmd --zone=public --add-port=5000/tcp --permanent  # 用户HTTP/WS登录端口 coco
    $ firewall-cmd --zone=public --add-port=8081/tcp --permanent  # guacamole端口 docker
      --permanent  永久生效，没有此参数重启后失效

    $ firewall-cmd --reload

    # selinux 的白名单规则正在研究中，稍后如果确定开启selinux不影响服务的正常使用会把相关文档补上来

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
