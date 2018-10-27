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

    # 设置 selinux 与 防火墙
    $ setenforce 0
    $ sed -i "s/enforcing/disabled/g" `grep enforcing -rl /etc/selinux/config`
    $ firewall-cmd --zone=public --add-port=8081/tcp --permanent
    $ firewall-cmd --reload

    $ yum -y localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-7.noarch.rpm
    $ rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
    $ rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm

    $ yum install -y git gcc java-1.8.0-openjdk libtool
    $ yum install -y cairo-devel libjpeg-turbo-devel libpng-devel uuid-devel
    $ yum install -y ffmpeg-devel freerdp-devel pango-devel libssh2-devel libtelnet-devel libvncserver-devel pulseaudio-libs-devel openssl-devel libvorbis-devel libwebp-devel

    $ cd /opt
    $ git clone https://github.com/jumpserver/docker-guacamole.git

    $ cd /opt/docker-guacamole/
    $ tar -xf guacamole-server-0.9.14.tar.gz
    $ cd guacamole-server-0.9.14
    $ autoreconf -fi
    $ ./configure --with-init-dir=/etc/init.d
    $ make && make install
    $ cd ..
    $ rm -rf guacamole-server-0.9.14.tar.gz guacamole-server-0.9.14
    $ ldconfig

    $ mkdir -p /config/guacamole /config/guacamole/lib /config/guacamole/extensions  # 创建 guacamole 目录
    $ cp /opt/docker-guacamole/guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar
    $ cp /opt/docker-guacamole/root/app/guacamole/guacamole.properties /config/guacamole/  # guacamole 配置文件

    $ cd /config
    $ wget http://mirror.bit.edu.cn/apache/tomcat/tomcat-8/v8.5.34/bin/apache-tomcat-8.5.34.tar.gz
    $ tar xf apache-tomcat-8.5.34.tar.gz
    $ rm -rf apache-tomcat-8.5.34.tar.gz
    $ mv apache-tomcat-8.5.34 tomcat8
    $ rm -rf /config/tomcat8/webapps/*
    $ cp /opt/docker-guacamole/guacamole-0.9.14.war /config/tomcat8/webapps/ROOT.war  # guacamole client
    $ sed -i 's/Connector port="8080"/Connector port="8081"/g' `grep 'Connector port="8080"' -rl /config/tomcat8/conf/server.xml`  # 修改默认端口为 8081
    $ sed -i 's/FINE/WARNING/g' `grep 'FINE' -rl /config/tomcat8/conf/logging.properties`  # 修改 log 等级为 WARNING

    $ export JUMPSERVER_SERVER=http://192.168.100.100  # 192.168.100.100 指 jumpserver 访问地址
    $ echo "export JUMPSERVER_SERVER=192.168.100.100" >> ~/.bashrc
    $ export JUMPSERVER_KEY_DIR=/config/guacamole/keys
    $ echo "export JUMPSERVER_KEY_DIR=/config/guacamole/keys" >> ~/.bashrc
    $ export GUACAMOLE_HOME=/config/guacamole
    $ echo "export GUACAMOLE_HOME=/config/guacamole" >> ~/.bashrc

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

    # 访问 http://192.168.100.100/terminal/terminal/ 接受 guacamole 注册

    # 多节点部署请参考此文档，部署方式一样，不需要做任何修改
