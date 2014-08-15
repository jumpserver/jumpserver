#!/bin/bash
username=$1
password=$2

cwd (){
    dir=$0
    dirname $dir
}

dir=$(cwd)
. ${dir}/shell.conf

if [ -z $1 ] || [ -z $2 ];then
    echo 
    echo "usage: ./useradd.sh username password"
    echo
    exit 3
fi

id $username &> /dev/null
if [ $? != '0' ];then
    useradd $username
    #ssh -p $host2_port $host2  "useradd $username"
    echo $password | passwd --stdin $username
else
    echo "$username have been exits."
    exit 5
fi

cd /usr/share/migrationtools/
./migrate_passwd.pl /etc/passwd > /tmp/passwd.ldif
./migrate_group.pl /etc/group > /tmp/group.ldif

grep -A15 "dn: uid=$username,ou=People,dc=yolu,dc=com" /tmp/passwd.ldif > /tmp/user.ldif
grep -A6 "dn: cn=$username,ou=Group,dc=yolu,dc=com" /tmp/group.ldif > /tmp/usergroup.ldif

ldapadd -x -h $host -w $ldapassword -D "cn=admin,dc=yolu,dc=com" -f /tmp/user.ldif
ldapadd -x -h $host -w $ldapassword -D "cn=admin,dc=yolu,dc=com" -f /tmp/usergroup.ldif
