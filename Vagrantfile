# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://vagrantcloud.com/search.
  config.vm.box_check_update = false
  config.vm.box = "centos/7"
  config.vm.hostname = "jumpserver"
  config.vm.network "private_network", ip: "172.17.8.101"
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "4096"
    vb.cpus = 2
    vb.name = "jumpserver"
  end

  config.vm.synced_folder ".", "/vagrant", type: "rsync",
    rsync__verbose: true,
    rsync__exclude: ['.git*', 'node_modules*','*.log','*.box','Vagrantfile']

  config.vm.provision "shell", inline: <<-SHELL
## 设置yum的阿里云源
sudo curl -o /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo
sudo sed -i -e '/mirrors.cloud.aliyuncs.com/d' -e '/mirrors.aliyuncs.com/d' /etc/yum.repos.d/CentOS-Base.repo
sudo curl -o /etc/yum.repos.d/epel.repo http://mirrors.aliyun.com/repo/epel-7.repo
sudo yum makecache

## 安装依赖包
sudo yum install -y python36 python36-devel python36-pip \
		 libtiff-devel libjpeg-devel libzip-devel freetype-devel \
     lcms2-devel libwebp-devel tcl-devel tk-devel sshpass \
     openldap-devel mariadb-devel mysql-devel libffi-devel \
     openssh-clients telnet openldap-clients gcc

## 配置pip阿里云源
mkdir /home/vagrant/.pip
cat << EOF | sudo tee -a /home/vagrant/.pip/pip.conf
[global]
timeout = 6000
index-url = https://mirrors.aliyun.com/pypi/simple/

[install]
use-mirrors = true
mirrors = https://mirrors.aliyun.com/pypi/simple/
trusted-host=mirrors.aliyun.com
EOF

python3.6 -m venv /home/vagrant/venv
source /home/vagrant/venv/bin/activate
echo 'source /home/vagrant/venv/bin/activate' >> /home/vagrant/.bash_profile
  SHELL
end
