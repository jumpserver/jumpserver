Ubuntu 16.04

$ apt-get -y install git libtool

$ apt-get -y install libcairo2-dev libjpeg-turbo8-dev libpng12-dev libossp-uuid-dev
$ apt-get -y install libavcodec-dev libavutil-dev libswscale-dev libfreerdp-dev libpango1.0-dev libssh2-1-dev libtelnet-dev libvncserver-dev libpulse-dev libssl-dev libvorbis-dev libwebp-dev

$ apt-get -y install default-jre
$ apt-get -y install default-jdk
$ apt-get -y install tomcat8

$ cd /opt
$ git clone https://github.com/jumpserver/docker-guacamole.git
$ tar xf guacamole-server-0.9.14.tar.gz
$ cd guacamole-server-0.9.14
$ autoreconf -fi
$ ./configure --with-init-dir=/etc/init.d
$ make && make install
$ ldconfig

$ rm -rf /var/lib/tomcat8/webapps/*
$ cp /opt/docker-guacamole/guacamole-0.9.14.war /var/lib/tomcat8/webapps/ROOT.war

$ mkdir -p /opt/guacamole /opt/guacamole/lib /opt/guacamole/extensions
$ cp /opt/docker-guacamole/guacamole-auth-jumpserver-0.9.14.jar /opt/guacamole/extensions/
$ cp /opt/docker-guacamole/root/app/guacamole/guacamole.properties /opt/guacamole/
$ chown -R tomcat8:tomcat8 /opt/guacamole

$ echo "JUMPSERVER_SERVER=http://127.0.0.1:8080" >> /etc/default/tomcat8
$ echo "JUMPSERVER_KEY_DIR=/opt/guacamole/key" >> /etc/default/tomcat8
$ echo "GUACAMOLE_HOME=/opt/guacamole" >> /etc/default/tomcat8

$ /etc/init.d/guacd restart
$ /etc/init.d/tomcat8 restart
