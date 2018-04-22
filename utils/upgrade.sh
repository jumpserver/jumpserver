#!/bin/bash

if [ ! -d "/opt/py3" ]; then
echo -e "\033[31m python3虚拟环境不是默认路径 \033[0m"
ps -ef | grep jumpserver/tmp/beat.pid | grep -v grep
if [ $? -ne 0 ]
then
echo -e "\033[31m jumpserver未运行，请到jumpserver目录使用 ./jms start all -d 启动 \033[0m"
exit 0
else 
echo -e "\033[31m 正在计算python3虚拟环境路径 \033[0m"
fi
py3pid=`ps -ef | grep jumpserver/tmp/beat.pid | grep -v grep | awk '{print $2}'`
py3file=`cat /proc/$py3pid/cmdline`
py3even=`echo ${py3file%/bin/python3*}`
echo -e "\033[31m python3虚拟环境路径为$py3even \033[0m"
source $py3even/bin/activate
else
source /opt/py3/bin/activate
fi

cd `dirname $0`/ && cd .. && ./jms stop

jumpserver_backup=/tmp/jumpserver_backup$(date -d "today" +"%Y%m%d_%H%M%S")
mkdir -p $jumpserver_backup
cp -r ./* $jumpserver_backup

echo -e "\033[31m 是否需要备份Jumpserver数据库 \033[0m"
stty erase ^H
read -p "确认备份请按Y，否则按其他键跳过备份 " a
if [ "$a" == y -o "$a" == Y ];then
echo -e "\033[31m 正在备份数据库 \033[0m"
echo -e "\033[31m 请手动输入数据库信息 \033[0m"
read -p '请输入Jumpserver数据库ip:' DB_HOST
read -p '请输入Jumpserver数据库端口:' DB_PORT
read -p '请输入Jumpserver数据库名称:' DB_NAME
read -p '请输入有权限导出数据库的用户:' DB_USER
read -p '请输入该用户的密码:' DB_PASSWORD
mysqldump -h$DB_HOST -P$DB_PORT -u$DB_USER -p$DB_PASSWORD $DB_NAME > /$jumpserver_backup/$DB_NAME$(date -d "today" +"%Y%m%d_%H%M%S").sql || {
echo -e "\033[31m 备份数据库失败，请检查输入是否有误 \033[0m"
exit 1
}
echo -e "\033[31m 备份数据库完成 \033[0m"

else
echo -e "\033[31m 已取消备份数据库操作 \033[0m"
fi

git pull && pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh

cd .. && ./jms start all -d
echo -e "\033[31m 请检查jumpserver是否启动成功 \033[0m"
echo -e "\033[31m 备份文件存放于$jumpserver_backup目录 \033[0m"

exit 0
