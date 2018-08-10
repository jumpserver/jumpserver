分布式部署文档 - guacamole 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.13

开始安装
~~~~~~~~~~~~

::

    # 升级系统
    $ yum upgrade -y

    # 安装依赖包
    $ yum install -y yum-utils device-mapper-persistent-data lvm2

    # 设置 selinux 策略
    $ chcon -Rt svirt_sandbox_file_t /opt/guacamole/key

    # 安装 docker（192.168.100.100 是 jumpserver 的 url 地址）
    $ yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    $ yum makecache fast
    $ yum install docker-ce
    $ systemctl start docker
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://192.168.100.100 \
      jumpserver/guacamole:latest

    # 访问 http://192.168.100.100/terminal/terminal/ 接受 guacamole 注册

    # 多节点部署请参考此文档，部署方式一样，不需要做任何修改
