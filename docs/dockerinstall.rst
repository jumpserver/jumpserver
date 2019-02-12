Docker 安装
==========================

Jumpserver 封装了一个 All in one Docker,可以快速启动。该镜像集成了所需要的组件,支持使用外置 Database 和 Redis

Tips: 不建议在生产中使用, 因为所有软件都打包到一个Docker中了,不是Docker最佳实践,
生产中请使用 详细安装 `CentOS <step_by_step.rst>`_  `Ubuntu <setup_by_ubuntu.rst>`_
Docker 安装见: `Docker官方安装文档 <https://docs.docker.com/install/>`_


快速启动
```````````````
使用 root 命令行输入

.. code-block:: shell

    # 最新版本
    $ docker run --name jms_all -d -p 80:80 -p 2222:2222 jumpserver/jms_all:latest

访问
```````````````

浏览器访问: http://<容器所在服务器IP>

SSH访问: ssh -p 2222 <容器所在服务器IP>

XShell等工具请添加 connection 连接, 默认 ssh 端口 2222

默认管理员账户 admin 密码 admin

外置数据库要求
```````````````
- mysql 版本需要大于等于 5.6
- mariadb 版本需要大于等于 5.5.6
- PostgreSQL 版本需要大于等于 9.4
- 数据库编码要求 uft8

创建数据库
``````````````````
创建数据库命令行

.. code-block:: shell

    # mysql
    $ create database jumpserver default charset 'utf8';
    $ grant all on jumpserver.* to 'jumpserver'@'%' identified by 'weakPassword';


额外环境变量
```````````````
- BOOTSTRAP_TOKEN = nwv4RdXpM82LtSvmV
- DB_ENGINE = mysql
- DB_HOST = mysql_host
- DB_PORT = 3306
- DB_USER = jumpserver
- DB_PASSWORD = weakPassword
- DB_NAME = jumpserver

- REDIS_HOST = 127.0.0.1
- REDIS_PORT = 6379
- REDIS_PASSWORD =

- VOLUME /opt/jumpserver/data
- VOLUME /var/lib/mysql

.. code-block:: shell

    $ docker run --name jms_all -d \
        -v /opt/mysql:/var/lib/mysql
        -p 80:80 \
        -p 2222:2222 \
        -e BOOTSTRAP_TOKEN=xxx
        -e DB_ENGINE=mysql \
        -e DB_HOST=192.168.x.x \
        -e DB_PORT=3306 \
        -e DB_USER=root \
        -e DB_PASSWORD=xxx \
        -e DB_NAME=jumpserver \
        -e REDIS_HOST=192.168.x.x \
        -e REDIS_PORT=6379 \
        -e REDIS_PASSWORD=xxx \
        jumpserver/jms_all:latest

仓库地址
```````````````

https://github.com/jumpserver/Dockerfile
