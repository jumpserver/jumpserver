CentOS 7 安装文档
--------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  > 开头的行表示需要在 mysql 中执行
-  $ 开头的行表示需要执行的命令

本文档适用于有一定web运维经验的管理员或者工程师,文中不会对安装的软件做过多的解释,仅对需要执行的内容注部分注释,更详细的内容请参考一步一步安装。

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

.. code-block:: shell

    $ yum update -y

    # 防火墙 与 selinux 设置说明,如果已经关闭了 防火墙 和 Selinux 的用户请跳过设置
    $ systemctl start firewalld
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent  # nginx 端口
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent  # 用户SSH登录端口 coco
      --permanent  永久生效,没有此参数重启后失效

    $ firewall-cmd --reload  # 重新载入规则

    $ setenforce 0
    $ sed -i "s/enforcing/disabled/g" `grep enforcing -rl /etc/selinux/config`

    # 修改字符集,否则可能报 input/output error的问题,因为日志里打印了中文
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf

    # 安装依赖包
    $ yum -y install wget gcc epel-release git

    # 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke
    $ yum -y install redis
    $ systemctl enable redis
    $ systemctl start redis

    # 安装 MySQL,如果不使用 Mysql 可以跳过相关 Mysql 安装和配置,支持sqlite3, mysql, postgres等
    $ yum -y install mariadb mariadb-devel mariadb-server # centos7下叫mariadb,用法与mysql一致
    $ systemctl enable mariadb
    $ systemctl start mariadb
    # 创建数据库 Jumpserver 并授权
    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'weakPassword';
    > flush privileges;
    > quit;

    # 安装 Nginx ,用作代理服务器整合 Jumpserver 与各个组件
    $ vi /etc/yum.repos.d/nginx.repo

    [nginx]
    name=nginx repo
    baseurl=http://nginx.org/packages/centos/7/$basearch/
    gpgcheck=0
    enabled=1

    $ yum -y install nginx
    $ systemctl enable nginx

    # 安装 Python3.6
    $ yum -y install python36 python36-devel

    # 配置并载入 Python3 虚拟环境
    $ cd /opt
    $ python3.6 -m venv py3  # py3 为虚拟环境名称,可自定义
    $ source /opt/py3/bin/activate  # 退出虚拟环境可以使用 deactivate 命令

    # 看到下面的提示符代表成功,以后运行 Jumpserver 都要先运行以上 source 命令,载入环境后默认以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 下载 Jumpserver
    $ cd /opt/
    $ git clone https://github.com/jumpserver/jumpserver.git

    # 安装依赖 RPM 包
    $ yum -y install $(cat /opt/jumpserver/requirements/rpm_requirements.txt)

    # 安装 Python 库依赖
    $ pip install --upgrade pip setuptools
    $ pip install -r /opt/jumpserver/requirements/requirements.txt

.. code-block:: shell


    # 修改 Jumpserver 配置文件
    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py

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
        # Use it to encrypt or decrypt data

        # Jumpserver 使用 SECRET_KEY 进行加密,请务必修改以下设置
        # SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'
        SECRET_KEY = '请随意输入随机字符串(推荐字符大于等于 50位)'

        # Django security setting, if your disable debug model, you should setting that
        ALLOWED_HOSTS = ['*']

        # DEBUG 模式 True为开启 False为关闭,默认开启,生产环境推荐关闭
        # 注意：如果设置了DEBUG = False,访问8080端口页面会显示不正常,需要搭建 nginx 代理才可以正常访问
        DEBUG = os.environ.get("DEBUG") or False

        # 日志级别,默认为DEBUG,可调整为INFO, WARNING, ERROR, CRITICAL,默认INFO
        LOG_LEVEL = os.environ.get("LOG_LEVEL") or 'WARNING'
        LOG_DIR = os.path.join(BASE_DIR, 'logs')

        # 使用的数据库配置,支持sqlite3, mysql, postgres等,默认使用sqlite3
        # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases

        # 默认使用SQLite3,如果使用其他数据库请注释下面两行
        # DB_ENGINE = 'sqlite3'
        # DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')

        # 如果需要使用mysql或postgres,请取消下面的注释并输入正确的信息,本例使用mysql做演示(mariadb也是mysql)
        DB_ENGINE = os.environ.get("DB_ENGINE") or 'mysql'
        DB_HOST = os.environ.get("DB_HOST") or '127.0.0.1'
        DB_PORT = os.environ.get("DB_PORT") or 3306
        DB_USER = os.environ.get("DB_USER") or 'jumpserver'
        DB_PASSWORD = os.environ.get("DB_PASSWORD") or 'weakPassword'
        DB_NAME = os.environ.get("DB_NAME") or 'jumpserver'

        # Django 监听的ip和端口
        # ./manage.py runserver 127.0.0.1:8080
        HTTP_BIND_HOST = '0.0.0.0'
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

.. code-block:: shell

    # 生成数据库表结构和初始化数据
    $ cd /opt/jumpserver/utils
    $ bash make_migrations.sh

    # 运行 Jumpserver
    $ cd /opt/jumpserver
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d
    # 新版本更新了运行脚本,使用方式./jms start|stop|status|restart all  后台运行请添加 -d 参数

.. code-block:: shell

    # 安装 docker 部署 coco 与 guacamole
    $ yum install -y yum-utils device-mapper-persistent-data lvm2
    $ yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    $ yum makecache fast
    $ yum -y install docker-ce
    $ systemctl enable docker
    $ systemctl start docker

    # 注意,<Jumpserver_url> 请自行修改成 jumpserver 对外的访问地址,如 192.168.100.100:8080
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> wojiushixiaobai/coco:1.4.4
    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> wojiushixiaobai/guacamole:1.4.4

    # 允许 容器ip 访问宿主 8080 端口,(容器的 ip 可以进入容器查看)
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="172.17.0.2" port protocol="tcp" port="8080" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="172.17.0.3" port protocol="tcp" port="8080" accept"

    # 172.17.0.x 是docker容器默认的IP池

.. code-block:: shell

    # 安装 Web Terminal 前端: Luna  需要 Nginx 来运行访问 访问(https://github.com/jumpserver/luna/releases)下载对应版本的 release 包,直接解压,不需要编译
    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/v1.4.4/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

.. code-block:: shell

    # 配置 Nginx 整合各组件
    $ rm /etc/nginx/conf.d/default.conf

.. code-block:: shell

    $ vi /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;

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
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location / {
            proxy_pass http://localhost:8080;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }


.. code-block:: shell

    # 运行 Nginx
    $ nginx -t   # 确保配置没有问题, 有问题请先解决
    $ systemctl start nginx

    # 访问 http://192.168.244.144 (注意,没有 :8080,通过 nginx 代理端口进行访问)
    # 默认账号: admin 密码: admin  到会话管理-终端管理 接受 Coco Guacamole 等应用的注册
    # 测试连接
    $ ssh -p2222 admin@192.168.244.144
    $ sftp -P2222 admin@192.168.244.144
      密码: admin

    # 如果是用在 Windows 下,Xshell Terminal 登录语法如下
    $ ssh admin@192.168.244.144 2222
    $ sftp admin@192.168.244.144 2222
      密码: admin
      如果能登陆代表部署成功

    # sftp默认上传的位置在资产的 /tmp 目录下
    # windows拖拽上传的位置在资产的 Guacamole RDP上的 G 目录下

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
