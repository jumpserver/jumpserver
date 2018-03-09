一步一步安装
--------------------------

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.244.144
-  关闭 selinux 和防火墙

::

    # CentOS 7
    $ setenforce 0  # 可以设置配置文件永久关闭
    $ systemctl stop iptables.service
    $ systemctl stop firewalld.service

    # CentOS6
    $ setenforce 0
    $ service iptables stop

一. 准备 Python3 和 Python 虚拟环境
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1.1 安装依赖包**

::

    $ yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel epel-release

**1.2 编译安装**

::

    $ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
    $ tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1
    $ ./configure && make && make install

**1.3 建立 Python 虚拟环境**

因为 CentOS 6/7 自带的是 Python2，而 Yum 等工具依赖原来的 Python，为了不扰乱原来的环境我们来使用 Python 虚拟环境

::

    $ cd /opt
    $ python3 -m venv py3
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

二. 安装 Jumpserver 0.5.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**2.1 下载或 Clone 项目**

项目提交较多 git clone 时较大，你可以选择去 Github 项目页面直接下载zip包。

::

    $ cd /opt/
    $ git clone --depth=1 https://github.com/jumpserver/jumpserver.git && cd jumpserver && git checkout master

**2.2 安装依赖 RPM 包**

::

    $ cd /opt/jumpserver/requirements
    $ yum -y install $(cat rpm_requirements.txt)  # 如果没有任何报错请继续

**2.3 安装 Python 库依赖**

::

    $ pip install -r requirements.txt  # 不要指定-i参数，因为镜像上可能没有最新的包，如果没有任何报错请继续

**2.4 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke**

::

    $ yum -y install redis
    $ service redis start

**2.5 安装 MySQL**

本教程使用 Mysql 作为数据库，如果不使用 Mysql 可以跳过相关 Mysql 安装和配置

::

    # centos7
    $ yum -y install mariadb mariadb-devel mariadb-server # centos7下安装的是mariadb
    $ service mariadb start

    # centos6
    $ yum -y install mysql mysql-devel mysql-server
    $ service mysqld start

**2.6 创建数据库 Jumpserver 并授权**

::

    $ mysql
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'somepassword';

**2.7 修改 Jumpserver 配置文件**

::

    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py  # 我们计划修改 DevelopmentConfig中的配置，因为默认jumpserver是使用该配置，它继承自Config

**注意: 配置文件是 Python 格式，不要用 TAB，而要用空格**

::

    class DevelopmentConfig(Config):
        DEBUG = True
        DB_ENGINE = 'mysql'
        DB_HOST = '127.0.0.1'
        DB_PORT = 3306
        DB_USER = 'jumpserver'
        DB_PASSWORD = 'somepassword'
        DB_NAME = 'jumpserver'

    ...

    config = DevelopmentConfig()  # 确保使用的是刚才设置的配置文件

**2.8 生成数据库表结构和初始化数据**

::

    $ cd /opt/jumpserver/utils
    $ bash make_migrations.sh

**2.9 运行 Jumpserver**

::

    $ cd /opt/jumpserver
    $ python run_server.py all

运行不报错，请浏览器访问 http://192.168.244.144:8080/
(这里只是 Jumpserver, 没有 Web Terminal，所以访问 Web Terminal 会报错)

账号: admin 密码: admin

三. 安装 SSH Server 和 WebSocket Server: Coco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**3.1 下载或 Clone 项目**

新开一个终端，连接测试机，别忘了 source /opt/py3/bin/activate

::

    $ cd /opt
    $ git clone https://github.com/jumpserver/coco.git && cd coco && git checkout master


**3.2 安装依赖**

::

    $ cd /opt/coco/requirements
    $ yum -y  install $(cat rpm_requirements.txt)
    $ pip install -r requirements.txt

**3.3 查看配置文件并运行**

::

    $ cd /opt/coco
    $ cp conf_example.py conf.py
    $ python run_server.py

这时需要去 Jumpserver 管理后台-会话管理-终端管理（http://192.168.244.144:8080/terminal/terminal/）接受 Coco 的注册

::

    Coco version 0.4.0, more see https://www.jumpserver.org
    Starting ssh server at 0.0.0.0:2222
    Quit the server with CONTROL-C.

**3.4 测试连接**

::

    $ ssh -p2222 admin@192.168.244.144
    密码: admin

    如果是用在 Windows 下，Xshell Terminal 登录语法如下
    $ssh admin@192.168.244.144 2222
    密码: admin
    如果能登陆代表部署成功

四. 安装 Web Terminal 前端: Luna
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Luna 已改为纯前端，需要 Nginx 来运行访问

访问（https://github.com/jumpserver/luna/releases）下载对应 release 包，直接解压，不需要编译

4.1 解压 Luna

::

    $ pwd
    /opt/

    $ tar xvf luna.tar.gz
    $ ls /opt/luna
    ...

五. 安装 Windows 支持组件
~~~~~~~~~~~~~~~~~~~~~~~~~~

因为手动安装 guacamole 组件比较复杂，这里提供打包好的 docker 使用, 启动 guacamole

.. code:: shell



    docker run -d \
      -p 8081:8080 \
      -e JUMPSERVER_SERVER=http://<填写本机的IP地址>:8080 \
      registry.jumpserver.org/public/guacamole:latest

这里所需要注意的是 guacamole 暴露出来的端口是 8081，若与主机上其他端口冲突请自定义一下。

修改 JUMPSERVER SERVER 的配置，填上 Jumpserver 的内网地址

六. 配置 Nginx 整合各组件
~~~~~~~~~~~~~~~~~~~~~~~~~

6.1 安装 Nginx 根据喜好选择安装方式和版本

6.2 配置文件

::

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
            proxy_pass       http://localhost:5000/socket.io/;
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /guacamole/ {
            proxy_pass       http://localhost:8081/;
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
        }

        location / {
            proxy_pass http://localhost:8080;
        }
    }

6.3 运行 Nginx

6.4 访问 http://192.168.244.144
