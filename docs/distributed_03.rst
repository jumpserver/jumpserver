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
-  服务: MariaDB Galera Cluster

+----------+------------+-----------------+---------------+------------------------+
| Protocol | ServerName |        IP       |      Port     |         Used By        |
+==========+============+=================+===============+========================+
|    TCP   | Mariadb-01 | 192.168.100.10  |      3306     |        Jumpserver      |
+----------+------------+-----------------+---------------+------------------------+
|    TCP   | Mariadb-02 | 192.168.100.11  |      3306     |        Jumpserver      |
+----------+------------+-----------------+---------------+------------------------+
|    TCP   | Mariadb-03 | 192.168.100.12  |      3306     |        Jumpserver      |
+----------+------------+-----------------+---------------+------------------------+



开始安装
~~~~~~~~~~~~

.. code-block:: shell

    # 以下命令需要在三台数据库服务器分别执行
    $ yum upgrade -y

    # 添加 MariaDB 源
    $ vi /etc/yum.repos.d/MariaDB.repo
    [mariadb]
    name = MariaDB
    baseurl = http://mirrors.ustc.edu.cn/mariadb/yum/10.1/centos7-amd64
    gpgkey=http://mirrors.ustc.edu.cn/mariadb/yum/RPM-GPG-KEY-MariaDB
    gpgcheck=1

    # 安装 MariaDB Galera Cluster
    $ yum install -y mariadb mariadb-server mariadb-shared mariadb-common galera rsync

    # 设置 Firewalld 和 Selinux
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.0/24" port protocol="tcp" port="3306" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.0/24" port protocol="tcp" port="4567" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.0/24" port protocol="tcp" port="4568" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.0/24" port protocol="tcp" port="4444" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.0/24" port protocol="udp" port="4567" accept"
    # 192.168.100.0/24 为整个 Jumpserver 网络网段, 这里就偷懒了, 自己根据实际情况修改即可

    $ firewall-cmd --reload

    $ setenforce 0
    $ sed -i "s/SELINUX=enforcing/SELINUX=disabled/g" /etc/selinux/config

.. code-block:: shell

    # 在 192.168.100.10 上执行初始化命令
    $ systemctl start mariadb
    $ mysql_secure_installation  # 推荐设置 root 密码, 其他选项可以全部 y
    $ systemctl stop mariadb

.. code-block:: shell

    # 在 192.168.100.10 上执行以下命令
    $ vi /etc/my.cnf.d/server.cnf
    ...
    [galera]
    wsrep_on=ON
    wsrep_provider=/usr/lib64/galera/libgalera_smm.so
    wsrep_cluster_name=galera_cluster
    wsrep_cluster_address="gcomm://192.168.100.10,192.168.100.11,192.168.100.12"
    wsrep_node_name=Mariadb-01   # 注意这里改成本机 hostname
    wsrep_node_address=192.168.100.10   # 注意这里改成本机 ip
    binlog_format=row
    default_storage_engine=InnoDB
    innodb_autoinc_lock_mode=2
    ...

    # 在 192.168.100.11 上执行以下命令
    $ vi /etc/my.cnf.d/server.cnf
    ...
    [galera]
    wsrep_on=ON
    wsrep_provider=/usr/lib64/galera/libgalera_smm.so
    wsrep_cluster_name=galera_cluster
    wsrep_cluster_address="gcomm://192.168.100.10,192.168.100.11,192.168.100.12"
    wsrep_node_name=Mariadb-02   # 注意这里改成本机 hostname
    wsrep_node_address=192.168.100.11   # 注意这里改成本机 ip
    binlog_format=row
    default_storage_engine=InnoDB
    innodb_autoinc_lock_mode=2
    ...

    # 在 192.168.100.12 上执行以下命令
    $ vi /etc/my.cnf.d/server.cnf
    ...
    [galera]
    wsrep_on=ON
    wsrep_provider=/usr/lib64/galera/libgalera_smm.so
    wsrep_cluster_name=galera_cluster
    wsrep_cluster_address="gcomm://192.168.100.10,192.168.100.11,192.168.100.12"
    wsrep_node_name=Mariadb-03   # 注意这里改成本机 hostname
    wsrep_node_address=192.168.100.12   # 注意这里改成本机 ip
    binlog_format=row
    default_storage_engine=InnoDB
    innodb_autoinc_lock_mode=2

.. code-block:: shell

    # 在 192.168.100.10 上执行以下命令
    $ sudo -u mysql /usr/sbin/mysqld --wsrep-new-cluster &> /tmp/wsrep_new_cluster.log &
    $ disown $!
    $ tail -f /tmp/wsrep_new_cluster.log  # 如果出现 ready for connections, 表示启动成功

.. code-block:: shell

    # 在 192.168.100.11 和 192.168.100.12 启动 mariadb 服务
    $ systemctl start mariadb

.. code-block:: shell

    # 回到第一台服务器
    $ ps -ef | grep mysqld | grep -v grep | awk '{print $2}' | xargs kill -9
    $ systemctl start mariadb

.. code-block:: shell

    # 在任意数据库服务器执行以下命令验证 MariaDB Galera Cluster
    $ mysql -uroot -p -e "show status like 'wsrep_cluster_size'"  # 这里应该显示集群里有3个节点
    $ mysql -uroot -p -e "show status like 'wsrep_connected'"  # 这里应该显示ON
    $ mysql -uroot -p -e "show status like 'wsrep_incoming_addresses'"  # 这里应该显示3个ip
    $ mysql -uroot -p -e "show status like 'wsrep_local_state_comment'"  # 这里显示节点的同步状态

.. code-block:: shell

    # 创建 Jumpserver 数据库及授权
    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'192.168.100.%' identified by 'weakPassword';
    > flush privileges;
    > quit

之后去 nginx 设置 tcp 代理即可
