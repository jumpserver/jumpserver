一步一步安装(CentOS)
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

    # 修改字符集，否则可能报 input/output error的问题，因为日志里打印了中文
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG="zh_CN.UTF-8"' > /etc/locale.conf

    # CentOS6
    $ setenforce 0
    $ service iptables stop

    # 修改字符集，否则可能报 input/output error的问题，因为日志里打印了中文
    $ localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8
    $ export LC_ALL=zh_CN.UTF-8
    $ echo 'LANG=zh_CN.UTF-8' > /etc/sysconfig/i18n

一. 准备 Python3 和 Python 虚拟环境
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1.1 安装依赖包**

::

    $ yum -y install wget sqlite-devel xz gcc automake zlib-devel openssl-devel epel-release git

Yum 加速设置请参考 <http://mirrors.163.com/.help/centos.html>

**1.2 编译安装**

::

    $ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
    $ tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1
    $ ./configure && make && make install

    # 这里必须执行编译安装，否则在安装 Python 库依赖时会有麻烦...

**1.3 建立 Python 虚拟环境**

因为 CentOS 6/7 自带的是 Python2，而 Yum 等工具依赖原来的 Python，为了不扰乱原来的环境我们来使用 Python 虚拟环境

::

    $ cd /opt
    $ python3 -m venv py3
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

**1.4 自动载入 Python 虚拟环境配置**

此项仅为懒癌晚期的人员使用，防止运行 Jumpserver 时忘记载入 Python 虚拟环境导致程序无法运行。使用autoenv

::

    $ git clone git://github.com/kennethreitz/autoenv.git ~/.autoenv
    $ echo 'source ~/.autoenv/activate.sh' >> ~/.bashrc
    $ source ~/.bashrc

二. 安装 Jumpserver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**2.1 下载或 Clone 项目**

项目提交较多 git clone 时较大，你可以选择去 Github 项目页面直接下载zip包。

::

    $ cd /opt/
    $ git clone --depth=1 https://github.com/jumpserver/jumpserver.git && cd jumpserver && git checkout master
    $ echo "source /opt/py3/bin/activate" > /opt/jumpserver/.env  # 进入 jumpserver 目录时将自动载入 python 虚拟环境

    # 首次进入 jumpserver 文件夹会有提示，按 y 即可
    # Are you sure you want to allow this? (y/N) y

**2.2 安装依赖 RPM 包**

::

    $ cd /opt/jumpserver/requirements
    $ yum -y install $(cat rpm_requirements.txt)  # 如果没有任何报错请继续

**2.3 安装 Python 库依赖**

::

    $ pip install -r requirements.txt  # 不要指定-i参数，因为镜像上可能没有最新的包，如果没有任何报错请继续

Pip 加速设置请参考 <https://segmentfault.com/a/1190000011875306>

**2.4 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke**

::

    $ yum -y install redis
    $ systemctl start redis

    # centos6
    $ service redis start


**2.5 安装 MySQL**

本教程使用 Mysql 作为数据库，如果不使用 Mysql 可以跳过相关 Mysql 安装和配置

::

    # centos7
    $ yum -y install mariadb mariadb-devel mariadb-server # centos7下安装的是mariadb
    $ systemctl enable mariadb
    $ systemctl start mariadb

    # centos6
    $ yum -y install mysql mysql-devel mysql-server
    $ chkconfig mysqld on
    $ service mysqld start

**2.6 创建数据库 Jumpserver 并授权**

::

    $ mysql
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'somepassword';
    > flush privileges;

**2.7 修改 Jumpserver 配置文件**

::

    $ cd /opt/jumpserver
    $ cp config_example.py config.py
    $ vi config.py

    # 我们计划修改 DevelopmentConfig 中的配置，因为默认 Jumpserver 使用该配置，它继承自 Config

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
    $ ./jms start all  # 后台运行使用 -d 参数./jms start all -d

    # 新版本更新了运行脚本，使用方式./jms start|stop|status|restart all  后台运行请添加 -d 参数

运行不报错，请浏览器访问 http://192.168.244.144:8080/  默认账号: admin 密码: admin 页面显示不正常先不用处理，搭建 nginx 代理就可以正常访问了

附上重启的方法

::

    $ ./jms restart

三. 安装 SSH Server 和 WebSocket Server: Coco
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**3.1 下载或 Clone 项目**

新开一个终端，连接测试机，别忘了 source /opt/py3/bin/activate

::

    $ cd /opt
    $ source /opt/py3/bin/activate
    $ git clone https://github.com/jumpserver/coco.git && cd coco && git checkout master
    $ echo "source /opt/py3/bin/activate" > /opt/coco/.env  # 进入 coco 目录时将自动载入 python 虚拟环境

    # 首次进入 coco 文件夹会有提示，按 y 即可
    # Are you sure you want to allow this? (y/N) y

**3.2 安装依赖**

::

    $ cd /opt/coco/requirements
    $ yum -y  install $(cat rpm_requirements.txt)
    $ pip install -r requirements.txt -i https://pypi.org/simple

**3.3 查看配置文件并运行**

::

    $ cd /opt/coco
    $ cp conf_example.py conf.py  # 如果 coco 与 jumpserver 分开部署，请手动修改 conf.py
    $ ./cocod start  # 后台运行使用 -d 参数./cocod start -d

    # 新版本更新了运行脚本，使用方式./cocod start|stop|status|restart  后台运行请添加 -d 参数

启动成功后去Jumpserver 会话管理-终端管理（http://192.168.244.144:8080/terminal/terminal/）接受coco的注册，如果页面不正常可以等部署完成后再处理

四. 安装 Web Terminal 前端: Luna
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Luna 已改为纯前端，需要 Nginx 来运行访问

访问（https://github.com/jumpserver/luna/releases）下载对应版本的 release 包，直接解压，不需要编译

4.1 解压 Luna

::

    $ pwd
    /opt/

    $ wget https://github.com/jumpserver/luna/releases/download/1.3.0/dist.tar.gz
    $ tar xvf dist.tar.gz
    $ mv dist luna
    $ ls /opt/luna
    ...

五. 安装 Windows 支持组件（如果不需要管理 windows 资产，可以直接跳过这一步）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

因为手动安装 guacamole 组件比较复杂，这里提供打包好的 docker 使用, 启动 guacamole

5.1 Docker安装 (仅针对CentOS7，CentOS6安装Docker相对比较复杂)

::

    $ yum remove docker-latest-logrotate  docker-logrotate  docker-selinux dockdocker-engine
    $ yum install -y yum-utils   device-mapper-persistent-data   lvm2

    # 添加docker官方源
    $ yum-config-manager     --add-repo     https://download.docker.com/linux/centos/docker-ce.repo
    $ yum makecache fast
    $ yum install docker-ce


    # 国内部分用户可能无法连接docker官网提供的源，这里提供阿里云的镜像节点供测试使用
    $ yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    $ rpm --import http://mirrors.aliyun.com/docker-ce/linux/centos/gpg
    $ yum makecache fast
    $ yum -y install docker-ce

    $ systemctl start docker
    $ systemctl status docker

5.2 启动 Guacamole

这里所需要注意的是 guacamole 暴露出来的端口是 8081，若与主机上其他端口冲突请自定义

修改下面 docker run 里的 JUMPSERVER_SERVER 参数，填上 Jumpserver 的 url 地址, 启动成功后去
Jumpserver 会话管理-终端管理（http://192.168.244.144:8080/terminal/terminal/）接受[Gua]开头的一个注册，如果页面显示不正常可以等部署完成后再处理

.. code:: shell


    # 注意：这里需要修改下 http://<填写jumpserver的url地址> 例: http://192.168.244.144, 否则会出错, 带宽有限, 下载时间可能有点长，可以喝杯咖啡，撩撩对面的妹子

    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写jumpserver的url地址> \
      registry.jumpserver.org/public/guacamole:latest

六. 配置 Nginx 整合各组件
~~~~~~~~~~~~~~~~~~~~~~~~~

6.1 安装 Nginx 根据喜好选择安装方式和版本

.. code:: shell

    $ yum -y install nginx


6.2 准备配置文件 修改 /etc/nginx/nginx.conf

内容如下：

::

    $ vim /etc/nginx/nginx.conf

    ... 省略
    # 把默认server配置块改成这样

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
            proxy_pass       http://localhost:8081/;  # 如果guacamole安装在别的服务器，请填写它的ip
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

    ... 省略

6.3 运行 Nginx

::

    nginx -t   # 确保配置没有问题, 有问题请先解决

    # CentOS 7
    $ systemctl start nginx
    $ systemctl enable nginx


    # CentOS 6
    $ service nginx start
    $ chkconfig nginx on

6.4 开始使用 Jumpserver

检查应用是否已经正常运行

::


    $ cd /opt/jumpserver
    $ ./jms status  # 确定jumpserver已经运行，如果没有运行请重新启动jumpserver

    $ cd /opt/coco
    $ ./cocod status  # 确定jumpserver已经运行，如果没有运行请重新启动coco

    # 如果安装了 Guacamole
    $ docker ps  # 检查容器是否已经正常运行，如果没有运行请重新启动Guacamole

服务全部启动后，访问 http://192.168.244.144

默认账号: admin 密码: admin

如果部署过程中没有接受应用的注册，需要到Jumpserver 会话管理-终端管理 接受 Coco Guacamole 等应用的注册。

** 测试连接**

::

    如果登录客户端是 macOS 或 Linux ，登录语法如下
    $ ssh -p2222 admin@192.168.244.144
    $ sftp -P2222 admin@192.168.244.144
    密码: admin

    如果登录客户端是 Windows ，Xshell Terminal 登录语法如下
    $ ssh admin@192.168.244.144 2222
    $ sftp admin@192.168.244.144 2222
    密码: admin
    如果能登陆代表部署成功

    # sftp默认上传的位置在资产的 /tmp 目录下

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
