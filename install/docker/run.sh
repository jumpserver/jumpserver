#!/bin/sh
cp -r /jumpserver/install/docker/config_tmpl.conf /jumpserver/jumpserver.conf
if [ ! -n "${USE_MYSQL}" ]; then
sed -i "s/__USE_MYSQL__/false/" /jumpserver/jumpserver.conf
else
sed -i "s/__MYSQL_ENGINE__/${MYSQL_ENGINE}/" /jumpserver/jumpserver.conf
sed -i "s/__MYSQL_HOST__/${MYSQL_HOST}/" /jumpserver/jumpserver.conf
sed -i "s/__MYSQL_PORT__/${MYSQL_PORT}/" /jumpserver/jumpserver.conf
sed -i "s/__MYSQL_USER__/${MYSQL_USER}/" /jumpserver/jumpserver.conf
sed -i "s/__MYSQL_PASS__/${MYSQL_PASS}/" /jumpserver/jumpserver.conf
sed -i "s/__MYSQL_NAME__/${MYSQL_NAME}/" /jumpserver/jumpserver.conf
fi

if [ ! -n "${USE_MAIL}" ]; then
sed -i "s/__USE_MAIL__/false/" /jumpserver/jumpserver.conf
else
sed -i "s/__MAIL_ENABLED__/${MAIL_ENABLED}/" /jumpserver/jumpserver.conf
sed -i "s/__MAIL_HOST__/${MAIL_HOST}/" /jumpserver/jumpserver.conf
sed -i "s/__MAIL_PORT__/${MAIL_PORT}/" /jumpserver/jumpserver.conf
sed -i "s/__MAIL_USER__/${MAIL_USER}/" /jumpserver/jumpserver.conf
sed -i "s/__MAIL_PASS__/${MAIL_PASS}/" /jumpserver/jumpserver.conf
fi
if [ ! -n "${MAIL_USE_TLS}" ]; then
sed -i "s/__MAIL_USE_TLS__/false/" /jumpserver/jumpserver.conf
else
sed -i "s/__MAIL_USE_TLS__/${MAIL_USE_TLS}/" /jumpserver/jumpserver.conf
fi
if [ ! -n "${MAIL_USE_SSL}" ]; then
sed -i "s/__MAIL_USE_SSL__/false/" /jumpserver/jumpserver.conf
else
sed -i "s/__MAIL_USE_SSL__/${MAIL_USE_SSL}/" /jumpserver/jumpserver.conf
fi
if [ ! -f "/etc/ssh/sshd_config" ]; then
	cp -r /jumpserver/install/docker/sshd_config /etc/ssh/sshd_config
fi
if [ ! -f "/etc/ssh/ssh_host_rsa_key" ]; then
  ssh-keygen -t rsa -b 2048 -f /etc/ssh/ssh_host_rsa_key -N ''
fi
if [ ! -f "/etc/ssh/ssh_host_dsa_key" ]; then
  ssh-keygen -t dsa -b 1024 -f /etc/ssh/ssh_host_dsa_key -N ''
fi
if [ ! -f "/etc/ssh/ssh_host_ecdsa_key" ]; then
  ssh-keygen -t ecdsa -b 521 -f /etc/ssh/ssh_host_ecdsa_key -N ''
fi
if [ ! -f "/etc/ssh/ssh_host_ed25519_key" ]; then
  ssh-keygen -t ed25519 -b 1024 -f /etc/ssh/ssh_host_ed25519_key -N ''
fi

/usr/sbin/sshd -E /data/logs/jumpserver.log
python /jumpserver/manage.py syncdb --noinput
if [ ! -f "/home/init.locked" ]; then
	python /jumpserver/manage.py loaddata install/initial_data.yaml
	date > /home/init.locked
fi
python /jumpserver/manage.py crontab add >> /data/logs/jumpserver.log &
python /jumpserver/run_server.py >> /dev/null &
chmod -R 777 /data/logs/jumpserver.log
tail -f /data/logs/jumpserver.log
