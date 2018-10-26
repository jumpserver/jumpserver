Centos 7

$ rpm –import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
$ rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm

$ yum install -y git gcc java-1.8.0-openjdk libtool epel-release tomcat
$ yum install -y cairo-devel libjpeg-turbo-devel libpng-devel uuid-devel
$ yum install -y freerdp-devel pango-devel libssh2-devel libvncserver-devel pulseaudio-libs-devel openssl-devel libvorbis-devel libwebp-devel

$ sed -i 's/Connector port="8080"/Connector port="8081"/g' `grep 'Connector port="8080"' -rl /etc/tomcat/server.xml`

cd /opt
$ git clone https://github.com/jumpserver/docker-guacamole.git

$ cd /opt/docker-guacamole/guacamole-server-0.9.14.tar.gz
$ tar -xzf guacamole-server-0.9.14.tar.gz
$ cd guacamole-server-0.9.14
$ autoreconf -fi
$ ./configure --with-init-dir=/etc/init.d
$ make
$ make install
$ cd ..
$ rm -rf guacamole-server-0.9.14.tar.gz guacamole-server-0.9.14 \
$ ldconfig

$ mkdir -p /opt/guacamole /opt/guacamole/lib /opt/guacamole/extensions
$ rm -rf /var/lib/tomcat/webapps/ROOT.war
$ cp /opt/docker-guacamole/guacamole-0.9.14.war /var/lib/tomcat/webapps/ROOT.war

$ cp /opt/docker-guacamole/guacamole-auth-jumpserver-0.9.14.jar /opt/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar

$ cp /opt/docker-guacamole/root/app/guacamole/guacamole.properties /opt/guacamole/

$ echo 'export JUMPSERVER_KEY_DIR=/config/guacamole/keys' >> /etc/tomcat/tomcat.conf
$ echo 'export GUACAMOLE_HOME=/config/guacamole' >> /etc/tomcat/tomcat.conf
$ echo 'export JUMPSERVER_SERVER=http://172.16.64.101:8080' >> /etc/tomcat/tomcat.conf

/etc/init.d/guacd start
systemctl start tomcat
