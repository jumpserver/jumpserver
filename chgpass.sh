#!/bin/bash
username=$1
password=$2

cwd (){
    dir=$0
    dirname $dir
}

dir=$(cwd)
. ${dir}/shell.conf

id ${username} &> /dev/null
if [ $? != 0 ];then
    echo "$username is not exist."
    exit 3
fi

echo "$password" | passwd --stdin "$username"

ssh -p $host2_port $host2 "echo \"$password\" | passwd --stdin \"$username\""