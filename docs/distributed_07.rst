分布式部署文档 - guacamole 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.50

+----------+------------+-----------------+---------------+------------------------+
| Protocol | ServerName |        IP       |      Port     |         Used By        |
+==========+============+=================+===============+========================+
|    TCP   | Guacamole  | 192.168.100.40  |      8081     |          Nginx         |
+----------+------------+-----------------+---------------+------------------------+
|    TCP   | Guacamole1 | 192.168.100.40  |      8082     |          Nginx         |
+----------+------------+-----------------+---------------+------------------------+


开始安装
~~~~~~~~~~~~

.. code-block:: shell

    # 升级系统
    $ yum upgrade -y

    # 设置防火墙, 开放 8081 端口 给 nginx 访问
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.100" port protocol="tcp" port="8081" accept"
    $ firewall-cmd --reload

    # 安装 docker
    $ sudo yum install -y yum-utils device-mapper-persistent-data lvm2
    $ yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    $ yum makecache fast
    $ yum -y install docker-ce
    $ curl -sSL https://get.daocloud.io/daotools/set_mirror.sh | sh -s http://f1361db2.m.daocloud.io
    $ systemctl enable docker
    $ systemctl start docker

    # 通过 docker 部署
    $ docker run --name jms_guacamole -d \
        -p 8081:8081 \
        -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
        -e JUMPSERVER_SERVER=http://192.168.100.30:8080 \
        -e BOOTSTRAP_TOKEN=你的token \
        jumpserver/jms_guacamole:1.5.0

    # 访问 http://192.168.100.100/terminal/terminal/ 检查 guacamole 注册


多节点部署
~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.100" port protocol="tcp" port="8082" accept"
    $ firewall-cmd --reload
    $ docker run --name jms_guacamole1 -d \
        -p 8082:8081 \
        -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
        -e JUMPSERVER_SERVER=http://192.168.100.30:8080 \
        -e BOOTSTRAP_TOKEN=你的token \
        jumpserver/jms_guacamole:1.5.0

    # 访问 http://192.168.100.100/terminal/terminal/ 检查 guacamole 注册
