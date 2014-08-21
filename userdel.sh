#!/bin/bash
username=$1
password=$2

cwd (){
    dir=$0
    dirname $dir
}

dir=$(cwd)
. ${dir}/shell.conf

id $username &> /dev/null
if [ $? == '0' ];then
    userdel -r $username
    #ssh -p $host2_port $host2 "userdel -r $username"
else
    echo "$username is not exist."
fi
ldapdelete -x -h $host -D "cn=admin,dc=$domain,dc=$suffix" -w $ldapassword "uid=$username,ou=People,dc=$domain,dc=$suffix"
ldapdelete -x -h $host -D "cn=admin,dc=$domain,dc=$suffix" -w $ldapassword "cn=$username,ou=Group,dc=$domain,dc=$suffix"