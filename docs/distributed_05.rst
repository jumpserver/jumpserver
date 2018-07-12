分布式部署文档 - coco 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.12

开始安装
~~~~~~~~~~~~

::

    # 升级系统
    $ yum upgrade -y

    # 安装依赖包
    $ yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel epel-release git

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

    # 下载 coco
    $ git clone https://github.com/jumpserver/coco.git
    $ echo "source /opt/py3/bin/activate" > /opt/coco/.env
    $ cd /opt/coco && git checkout master && git pull
    # 首次进入 coco 文件夹会有提示，按 y 即可
    # Are you sure you want to allow this? (y/N) y

    # 安装依赖 RPM 包
    $ yum -y install $(cat /opt/coco/requirements/rpm_requirements.txt)

    # 安装 Python 库依赖
    $ pip install --upgrade pip && pip install -r /opt/coco/requirements/requirements.txt

    # # 修改 Coco 配置文件
    $ cd /opt/coco
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
        CORE_HOST = 'http://192.168.100.100'

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

    # 运行 coco
    $ cd /opt/coco
    $ ./cocod start all  # 后台运行使用 -d 参数./jms start all -d
    # 新版本更新了运行脚本，使用方式./jms start|stop|status all  后台运行请添加 -d 参数

    # 访问 http://192.168.100.100/terminal/terminal/ 接受 coco 注册

    # 多节点部署请参考此文档，部署方式一样
