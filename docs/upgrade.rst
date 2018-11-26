更新升级
-------------

1.0.x 升级到 1.4.4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 请先检查自己各组件的当前版本
- 不支持从 0.x 版本升级到 1.x 版本
- 本文档仅针对 1.0 及之后的版本升级教程
- 从 1.4.x 版本开始 mysql 版本需要大于等于 5.6,mariadb 版本需要大于等于 5.5.6

0. 检查数据库表结构文件是否完整

.. code-block:: shell

    # 为了保证能顺利升级,请先检查数据库表结构文件是否完整
    $ cd /opt/jumpserver/apps
    $ for d in $(ls); do if [ -d $d ] && [ -d $d/migrations ]; then ll ${d}/migrations/*.py | grep -v __init__.py; fi; done

    # 新开一个终端,连接到 jumpserver 的数据库服务器
    $ mysql -uroot -p
    > use jumpserver;
    > select app,name from django_migrations where app in('assets','audits','common','ops','orgs','perms','terminal','users') order by app asc;

    # 如果左右对比信息不一致,请勿升级,升级必然失败

1. 备份 Jumpserver 数据库表结构 (通过releases包升级需要还原这些文件)

.. code-block:: shell

    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ cd /opt/jumpserver/apps
    $ for d in $(ls);do
        if [ -d $d ] && [ -d $d/migrations ];then
          mkdir -p $jumpserver_backup/${d}/migrations
          cp ${d}/migrations/*.py $jumpserver_backup/${d}/migrations/
        fi
      done

.. code-block:: shell

    # 还原代码 (通过releases包升级需要还原这些文件,通过git pull升级不需要执行)
    $ cd $jumpserver_backup/
    $ for d in $(ls);do
        if [ -d $d ] && [ -d $d/migrations ];then
          cp ${d}/migrations/*.py /opt/jumpserver/apps/${d}/migrations/
        fi
      done

2. 升级 Jumpserver

.. code-block:: shell

    # 升级前请做好 jumpserver 与 数据库 备份,谨防意外,具体的备份命令可以参考离线升级
    $ cd /opt/jumpserver
    $ source /opt/py3/bin/activate
    $ git pull
    $ ./jms stop

.. code-block:: shell

    # jumpserver 版本小于 1.3 升级到最新版本请使用新的 config.py (升级前版本小于 1.3 需要执行此步骤,否则跳过)
    $ mv config.py config.bak
    $ cp config_example.py config.py
    $ vi config.py  # 参考安装文档进行修改

.. code-block:: shell

    # 所有版本都需要执行此步骤
    $ pip install -r requirements/requirements.txt
    $ cd utils && sh make_migrations.sh

.. code-block:: shell

    # 1.0.x 升级到最新版本需要执行迁移脚本 (新版本授权管理更新,升级前版本不是 1.0.x 请跳过)
    $ sh 2018_04_11_migrate_permissions.sh

.. code-block:: shell

    # 任意版本升级到 1.4.0 版本,需要执行(升级前版本小于 1.4.0 需要执行此步骤)
    $ sh 2018_07_15_set_win_protocol_to_ssh.sh

.. code-block:: shell

    # 启动 jumpserver
    $ cd ../
    $ ./jms start all

.. code-block:: nginx

    # 任意版本升级到 1.4.2 版本,需要修改 nginx 配置 (升级前版本小于 1.4.2 需要执行此步骤)
    $ vi /etc/nginx/conf.d/jumpserver.conf  # 部分用户的配置文件是/etc/nginx/nginx.conf

    ...

    location /socket.io/ {
        # 原来的内容,请参考安装文档 nginx 部分
    }

    # 加入下面内容
    location /coco/ {
        proxy_pass       http://localhost:5000/coco/;  # 如果coco安装在别的服务器,请填写它的ip
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        access_log off;
    }
    # 到此结束

    location /guacamole/ {
        # 原来的内容,请参考安装文档 nginx 部分
    }

    ...

.. code-block:: shell

    # 保存后重新载入配置
    $ nginx -s reload

3. 升级 Coco (docker 部署的请忽略往下看)

.. code-block:: shell

    # 如果 coco 目录非默认位置请手动修改
    $ cd /opt/coco
    $ source /opt/py3/bin/activate
    $ git pull
    $ ./cocod stop
    $ pip install -r requirements/requirements.txt

.. code-block:: shell

    # coco 升级前版本小于 1.4.1 升级到最新版本请使用新的 conf.py (升级前版本小于 1.4.1 需要执行此步骤)
    $ mv conf.py coco.bak
    $ cp conf_example.py conf.py
    $ vi conf.py  # 参考安装文档进行修改

    $ ./cocod start

4. 升级 guacamole (docker 部署的请忽略往下看)

.. code-block:: shell

    $ cd /opt/docker-guacamole
    $ git pull
    $ /etc/init.d/guacd stop
    $ sh /config/tomcat8/bin/shutdown.sh
    $ cp guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar

    $ cd /config
    $ wget https://github.com/ibuler/ssh-forward/releases/download/v0.0.5/linux-amd64.tar.gz
    $ tar xf linux-amd64.tar.gz -C /bin/
    $ chmod +x /bin/ssh-forward

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

5. 升级 Luna

重新下载 release 包(https://github.com/jumpserver/luna/releases)

.. code-block:: shell

    $ cd /opt
    $ rm -rf luna
    $ wget https://github.com/jumpserver/luna/releases/download/v1.4.4/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

    # 注意把浏览器缓存刷新下

6. Docker 部署 coco guacamole 升级说明

.. code-block:: shell

    # 先到 Web 会话管理 - 终端管理 删掉所有组件
    $ docker stop jms_coco
    $ docker stop jms_guacamole
    $ docker rm jms_coco
    $ docker rm jms_guacamole
    $ docker pull wojiushixiaobai/coco:1.4.4
    $ docker pull wojiushixiaobai/guacamole:1.4.4
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> wojiushixiaobai/coco:1.4.4
    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> wojiushixiaobai/guacamole:1.4.4

    # 到 Web 会话管理 - 终端管理 接受新的注册


1.4.4 升级到 1.4.5 (未开放, 等待更新)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 当前版本必须是 1.4.4 版本,否则请先升级到 1.4.4
- 从 1.4.5 版本开始,由官方维护唯一 migrations

**Jumpserver**

.. code-block:: shell

    $ cd /opt/jumpserver
    $ git pull
    $ source /opt/py3/bin/activate
    $ ./jms stop

.. code-block:: shell

    # 备份数据库表结构文件
    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ mv config.py $jumpserver_backup/
    $ cd /opt/jumpserver/apps
    $ for d in $(ls);do
        if [ -d $d ] && [ -d $d/migrations ];then
          mkdir -p $jumpserver_backup/${d}/migrations
          mv ${d}/migrations/*.py $jumpserver_backup/${d}/migrations/
        fi
      done

    $ sh utils/clean_migrations.sh

.. code-block:: shell

    $ cd /opt/jumpserver
    $ git pull

    # 更新 config.py ,请根据你原备份的 config.py 内容进行修改
    $ cp config_example.py config.py
    $ vi config.py

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

        # SECURITY WARNING: keep the bootstrap token used in production secret!
        # 预共享Token coco和guacamole用来注册服务账号，不在使用原来的注册接受机制
        BOOTSTRAP_TOKEN = '9JO4#n!Xup2zKZ6V'

        # Development env open this, when error occur display the full process track, Production disable it
        # DEBUG 模式 开启DEBUG后遇到错误时可以看到更多日志
        # DEBUG = True
        DEBUG = False

        # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
        # 日志级别
        # LOG_LEVEL = 'DEBUG'
        # LOG_DIR = os.path.join(BASE_DIR, 'logs')
        LOG_LEVEL = 'ERROR'

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

.. code-block:: shell

    $ pip install -r requirements/requirements.txt
    $ cd utils
    $ sh 1.4.4_to_1.4.5_migrations.sh
    $ sh make_migrations.sh

    $ cd ../
    $ ./jms start all -d

**Coco**

说明: Docker 部署的请跳过

.. code-block:: shell

    $ cd /opt/coco
    $ git pull
    $ source /opt/py3/bin/activate
    $ ./cocod stop

    $ mv conf.py $jumpserver_backup/

    # 更新 conf.py ,请根据你原备份的 conf.py 内容进行修改
    $ cp conf_example.py conf.py
    $ vi conf.py

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
        NAME = "coco"

        # Jumpserver项目的url, api请求注册会使用, 如果Jumpserver没有运行在127.0.0.1:8080,请修改此处
        # CORE_HOST = os.environ.get("CORE_HOST") or 'http://127.0.0.1:8080'
        CORE_HOST = 'http://127.0.0.1:8080'

        # Bootstrap Token, 预共享秘钥, 用来注册coco使用的service account和terminal
        # 请和jumpserver 配置文件中保持一致，注册完成后可以删除
        # BOOTSTRAP_TOKEN = "PleaseChangeMe"
        BOOTSTRAP_TOKEN = "9JO4#n!Xup2zKZ6V"

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

    $ pip install -r requirements/requirements.txt
    $ ./cocod start -d

**Guacamole**

说明: Docker 部署的请跳过

.. code-block:: shell

    $ cd /opt/docker-guacamole
    $ git pull
    $ /etc/init.d/guacd stop
    $ sh /config/tomcat8/bin/shutdown.sh
    $ cp -r guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar

    $ cd /config
    $ wget https://github.com/ibuler/ssh-forward/releases/download/v0.0.5/linux-amd64.tar.gz
    $ tar xf linux-amd64.tar.gz -C /bin/
    $ chmod +x /bin/ssh-forward

    $ export BOOTSTRAP_TOKEN=9JO4#n!Xup2zKZ6V
    $ echo "export BOOTSTRAP_TOKEN=9JO4#n!Xup2zKZ6V" >> ~/.bashrc

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

**Luna**

说明: 直接下载 release 包

.. code-block:: shell

    $ cd /opt
    $ rm -rf luna
    $ wget https://github.com/jumpserver/luna/releases/download/v1.4.5/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

**Docker Coco Guacamole**

说明: Docker 部署的 coco 与 guacamole 升级说明

.. code-block:: shell

    # 先到 Web 会话管理 - 终端管理 删掉所有组件
    $ docker sop jms_coco
    $ docker stop jms_guacamole
    $ docker rm jms_coco
    $ docker rm jms_guacamole
    $ docker pull wojiushixiaobai/coco:1.4.5
    $ docker pull wojiushixiaobai/guacamole:1.4.5
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> -e BOOTSTRAP_TOKEN=9JO4#n!Xup2zKZ6V wojiushixiaobai/coco:1.4.5
    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> -e BOOTSTRAP_TOKEN=9JO4#n!Xup2zKZ6V wojiushixiaobai/guacamole:1.4.5

    # 到 Web 会话管理 - 终端管理 查看组件是否已经在线


1.4.6 及之后版本升级说明 (未开放, 等待更新)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 如果当前版本必须小于 1.4.5 ,请先升级到 1.4.5
