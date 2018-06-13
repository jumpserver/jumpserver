分布式部署文档 - 数据库 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.10

开始安装
~~~~~~~~~~~~

::

    # 升级系统
    $ yum upgrade -y

    # 安装 mariadb 服务
    $ yum install -y install mariadb mariadb-devel mariadb-server

    # 设置防火墙，开发 3306 端口
    $ firewall-cmd --zone=public --add-port=3306/tcp --permanent
    $ firewall-cmd --reload

    # 设置 mariadb 服务
    $ systemctl enable mariadb
    $ systemctl start mariadb

    # 推荐使用该命令进行一些安全设置（可跳过）
    $ mysql_secure_installation

    # 创建数据库及授权，192.168.100.11 是 jumpserver 服务器的 ip
    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'192.168.100.11' identified by 'somepassword';
    > flush privileges;
    > quit
