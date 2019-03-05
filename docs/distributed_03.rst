分布式部署文档 - 数据库 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令
-  > 开头的行表示需要在数据库中执行

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.10

+----------+------------+-----------------+---------------+------------------------+
| Protocol | ServerName |        IP       |      Port     |         Used By        |
+==========+============+=================+===============+========================+
|    TCP   |    Mysql   | 192.168.100.10  |      3306     |        Jumpserver      |
+----------+------------+-----------------+---------------+------------------------+

开始安装
~~~~~~~~~~~~

.. code-block:: shell

    # 升级系统
    $ yum upgrade -y

    # 安装 mariadb 服务
    $ yum install -y install mariadb mariadb-devel mariadb-server

    # 设置防火墙, 开放 3306 端口 给 jumpserver 访问
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.30" port protocol="tcp" port="3306" accept"
    $ firewall-cmd --reload

    # 设置 mariadb 服务
    $ systemctl enable mariadb
    $ systemctl start mariadb

    # 推荐使用该命令进行一些安全设置(可跳过)
    $ mysql_secure_installation

.. code-block:: shell

    # 创建数据库及授权, 192.168.100.30 是 jumpserver 服务器的 ip
    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'192.168.100.30' identified by 'weakPassword';
    > flush privileges;
    > quit

    # 数据库的主从设置请参考其官方, 之后会补上
