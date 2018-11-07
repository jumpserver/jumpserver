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

开始安装
~~~~~~~~~~~~

::

    # 升级系统
    $ yum upgrade -y

    # 安装依赖包
    $ yum install -y yum-utils device-mapper-persistent-data lvm2

    # 设置防火墙，开放 8081 端口 给 nginx 和 jumpserver 访问
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.30" port protocol="tcp" port="8081" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.100" port protocol="tcp" port="8081" accept"
    $ firewall-cmd --reload

    # 安装 docker
    $ sudo yum install -y yum-utils device-mapper-persistent-data lvm2
    $ yum-config-manager --add-repo http://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    $ yum makecache fast
    $ yum -y install docker-ce
    $ systemctl start docker
    $ systemctl enable docker

    # 通过 docker 部署
    $ docker run --name jms_guacamole -d \
        -p 8081:8081 \
        -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
        -e JUMPSERVER_SERVER=http://192.168.100.30:8080 \
        wojiushixiaobai/guacamole:1.4.3

    # 访问 http://192.168.100.100/terminal/terminal/ 接受 guacamole 注册


多节点部署
~~~~~~~~~~~~~~~~~~

::

    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.30" port protocol="tcp" port="8082" accept"
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.100" port protocol="tcp" port="8082" accept"
    $ firewall-cmd --reload
    $ docker run --name jms_guacamole1 -d \
        -p 8082:8081 \
        -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
        -e JUMPSERVER_SERVER=http://192.168.100.30:8080 \
        wojiushixiaobai/guacamole:1.4.3

    # 访问 http://192.168.100.100/terminal/terminal/ 接受 guacamole 注册
