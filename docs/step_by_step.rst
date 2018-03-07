一步一步安装
--------------------------

环境
~~~~

-  系统: CentOS 7
-  IP: 192.168.244.144
-  关闭 selinux和防火墙

::

    # CentOS 7
    $ setenforce 0  # 可以设置配置文件永久关闭
    $ systemctl stop iptables.service
    $ systemctl stop firewalld.service

    # CentOS6
    $ setenforce 0
    $ service iptables stop

一. 准备Python3和Python虚拟环境
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1.1 安装依赖包**

::

    $ yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel epel-release

**1.2 编译安装**

::

    $ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
    $ tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1
    $ ./configure && make && make install

**1.3 建立python虚拟环境**

因为CentOS
6/7自带的是Python2，而Yum等工具依赖原来的Python，为了不扰乱原来的环境我们来使用Python虚拟环境

::

    $ cd /opt
    $ python3 -m venv py3
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功，以后运行jumpserver都要先运行以上source命令，以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]#

二. 安装Jumpserver 0.5.0
~~~~~~~~~~~~~~~~~~~~~~~~

**2.1 下载或clone项目**

项目提交较多git clone时较大，你可以选择去github项目页面直接下载
zip包，我的网速好，我直接clone了

::

    $ cd /opt/
    $ git clone --depth=1 https://github.com/jumpserver/jumpserver.git && cd jumpserver && git checkout dev

**2.2 安装依赖rpm包**

::

    $ cd /opt/jumpserver/requirements
    $ yum -y install $(cat rpm_requirements.txt)  # 如果没有任何报错请继续

**2.3 安装python库依赖**

::

    $ pip install -r requirements.txt  # 不要指定-i参数，因为镜像上可能没有最新的包，如果没有任何报错请继续

**2.4 安装Redis, jumpserver使用redis做cache和celery broker**

::

    $ yum -y install redis
    $ service redis start

**2.5 安装MySQL**

本教程使用mysql作为数据库，如果不使用mysql可以跳过相关mysql安装和配置

::

    # centos7
    $ yum -y install mariadb mariadb-devel mariadb-server # centos7下安装的是mariadb
    $ service mariadb start

    # centos6
    $ yum -y install mysql mysql-devel mysql-server
    $ service mysqld start

**2.6 创建数据库 jumpserver并授权**

::

    $ mysql
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'somepassword';

**2.7 修改jumpserver配置文件**

::

    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py  # 我们计划修改 DevelopmentConfig中的配置，因为默认jumpserver是使用该配置，它继承自Config

**注意: 配置文件是python格式，不要用tab，而要用空格** **注意:
配置文件是python格式，不要用tab，而要用空格** **注意:
配置文件是python格式，不要用tab，而要用空格**

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

**2.9 运行Jumpserver**

::

    $ cd /opt/jumpserver
    $ python run_server.py all

运行不报错，请浏览器访问 http://192.168.244.144:8080/
(这里只是jumpserver, 没有web terminal,所以访问web terminal会报错)

账号:admin 密码: admin

三. 安装 SSH Server和Web Socket Server: Coco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**3.1 下载clone项目**

新开一个终端，连接测试机，别忘了 source /opt/py3/bin/activate

::

    $ cd /opt
    $ git clone https://github.com/jumpserver/coco.git && cd coco && git checkout dev

**3.2 安装依赖**

::

    $ cd /opt/coco/requirements $ yum -y install $(cat rpm_requirements.txt) $ pip install requirements.txt


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

这时需要去
jumpserver管理后台-终端-终端(http://192.168.244.144:8080/terminal/terminal/)接受coco的注册

::

    Coco version 0.4.0, more see https://www.jumpserver.org
    Starting ssh server at 0.0.0.0:2222
    Quit the server with CONTROL-C.

**3.4 测试连接**

::

    $ ssh -p2222 admin@192.168.244.144
    密码: admin

    如果是用在windows下，Xshell terminal登录语法如下
    $ssh admin@192.168.244.144 2222
    密码: admin
    如果能登陆代表部署成功

四. 安装 Web Terminal 前端: Luna
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Luna已改为纯前端，需要nginx来运行访问

下载 release包，直接解压，不需要编译

访问 https://github.com/jumpserver/luna/releases，下载对应release包

4.1 解压luna

::

    $ pwd
    /opt/

    $ tar xvf luna.tar.gz
    $ ls /opt/luna
    ...

五. 安装Windows支持组件
~~~~~~~~~~~~~~~~~~~~~~~

使用docker启动 guacamole

.. code:: shell

    docker run \
      -p 8080:8080 \
      -e JUMPSERVER_SERVER=http://<jumpserver>:8080 \
      jumpserver/guacamole

这里所需要注意的是guacamole暴露出来的端口是8080，若与jumpserver部署在同一主机上自定义一下。

修改JUMPSERVER_SERVER的配置，填上jumpserver的内网地址

六. 配置 nginx 整合各组件
~~~~~~~~~~~~~~~~~~~~~~~~~

6.1 安装nginx 根据喜好选择安装方式和版本

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
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /guacamole/ {
            proxy_pass http://<guacamole>:8080/;
        }

        location / {
            proxy_pass http://localhost:8080;
        }
    }

6.3 运行 nginx

6.4 访问 http://192.168.244.144