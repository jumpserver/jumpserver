服务迁移
-------------

对 Jumpserver 服务进行迁移, 只需要备份 "数据库" 和 "jumpserver目录" 即可
注：1.4.5 及之后的版本迁移, 只需要迁移 "数据库" "配置文件" 和 "录像目录"

1. 备份数据到新的服务器

.. code-block:: shell

    # 导出 jumpserver 数据库到新的服务器
    $ mysqldump -uroot -p jumpserver > /opt/jumpserver.sql
    # 把 jumpserver.sql 拷贝到新的服务器 /opt 目录
    # 复制 Jumpserve 目录到新的服务器 /opt 目录

2. 配置新服务器 (注意 mysql-server 的版本要与旧服务器一致)

.. code-block:: shell

    $ yum -y install wget gcc epel-release git
    $ yum -y install mariadb mariadb-devel mariadb-server mariadb-shared
    $ yum -y install redis

    $ systemctl enable redis
    $ systemctl enable mariadb
    $ systemctl start redis
    $ systemctl start mariadb

    $ mysql -uroot
    > create database jumpserver default charset 'utf8';
    > grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'weakPassword';
    > use jumpserver;
    > source /opt/jumpserver.sql;
    > quit

    $ yum -y install python36 python36-devel

    $ cd /opt
    $ python3.6 -m venv py3
    $ source /opt/py3/bin/activate

    $ cd /opt/jumpserver/requirements
    $ yum -y install $(cat rpm_requirements.txt)
    $ pip install --upgrade pip setuptools
    $ pip install -r requirements.txt

3. 修改配置文件

.. code-block:: shell

    $ cd /opt/jumpserver
    $ vi config.yml
    # 把数据库和 redis 信息修改并保存

4. 启动 jumpserver

.. code-block:: shell

    $ ./jms start all

5. 其他组件参考安装文档重新设置即可
