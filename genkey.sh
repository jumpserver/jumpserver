#!/bin/bash
user=$1
password=$2

cwd (){
    dir=$0
    dirname $dir
}

dir=$(cwd)
. ${dir}/shell.conf

keyfile=${dir}/keys/${user}
rm -f ${keyfile}

gen_key() {
    ssh-keygen -t rsa -f ${keyfile} -P $1
}

if [ -z $1 ] || [ -z $2 ];then
    echo "Usage: ./script user password"
    exit 3
fi

gen_key ${password}

mkdir -p /home/${user}/.ssh
#ssh -p ${host2_port} ${host2} "mkdir -p /home/$user/.ssh"

cat ${keyfile}.pub > /home/${user}/.ssh/authorized_keys
#ssh -p ${host2_port} ${host2} "cat > /home/$user/.ssh/authorized_keys" < ${keyfile}.pub

chmod 600 /home/${user}/.ssh/authorized_keys
#ssh -p ${host2_port} ${host2} "chmod 600 /home/$user/.ssh/authorized_keys"

chown -R ${user}:${user} /home/${user}/.ssh
#ssh -p ${host2_port} ${host2} "chown -R $user:$user /home/$user/.ssh"