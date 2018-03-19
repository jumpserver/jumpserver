一步一步安装

环境
系统: Ubuntu 16.04
IP: 192.168.244.144

推荐硬件：
CPU:64位双核处理器
内存:4G DDR3


$ apt-get update && apt-get -y upgrade
一. 准备 Python3 和 Python 虚拟环境
1.1 安装依赖包
$ apt-get -y install wget libkrb5-dev libsqlite3-dev gcc make automake libssl-dev zlib1g-dev libmysqlclient-dev libffi-dev git

1.2 编译安装
$ wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tar.xz
$ tar xvf Python-3.6.1.tar.xz  && cd Python-3.6.1
$ ./configure && make && make install

1.3 建立 Python 虚拟环境
$ cd /opt
$ python3.6 -m venv py3
$ source /opt/py3/bin/activate
# 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，以下所有命令均在该虚拟环境中运行
(py3) [root@localhost py3]

二. 安装 Jumpserver 1.0.0
2.1 下载或 Clone 项目
$ cd /opt/
$ git clone --depth=1 https://github.com/jumpserver/jumpserver.git && cd jumpserver && git checkout master

2.2 安装依赖 DEB 包
$ cd /opt/jumpserver/requirements
$ apt-get -y install $(cat deb_requirements.txt)  # 如果没有任何报错请继续

2.3 安装 Python 库依赖
$ pip install -r requirements.txt  # 不要指定-i参数，因为镜像上可能没有最新的包，如果没有任何报错请继续

2.4 安装 Redis, Jumpserver 使用 Redis 做 cache 和 celery broke
$ apt-get -y install redis-server

2.5 安装 MySQL
本教程使用 Mysql 作为数据库，如果不使用或 Mysql数据库 不在本地可以跳过相关 Mysql 安装和配置
$ apt-get -y install mysql-server  # 安装过程中注意输入数据库 root账户 的密码

2.6 创建数据库 Jumpserver 并授权
$ mysql -uroot -p
> create database jumpserver default charset 'utf8';
> grant all on jumpserver.* to 'jumpserver'@'127.0.0.1' identified by 'somepassword';
> flush privileges;

2.7 修改 Jumpserver 配置文件
$ cd /opt/jumpserver
$ cp config_example.py config.py
$ vim config.py  # 我们只修改 数据库 的配置，默认jumpserver是使用 sqlite3 配置，我们更改为 mysql

class Config:

...

    # DB_ENGINE = 'sqlite3'
    # DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')

    DEBUG = True
    DB_ENGINE = 'mysql'
    DB_HOST = '127.0.0.1'
    DB_PORT = 3306
    DB_USER = 'jumpserver'
    DB_PASSWORD = 'somepassword'
    DB_NAME = 'jumpserver'

...

config = DevelopmentConfig()  # 确保使用的是刚才设置的配置文件

2.8 生成数据库表结构和初始化数据
$ cd /opt/jumpserver/utils
$ bash make_migrations.sh  # 如果环境配置过低，这里会卡住一会，属于正常现象

2.9 运行 Jumpserver
$ cd /opt/jumpserver
$ python run_server.py all
运行不报错，请浏览器访问 http://192.168.244.144:8080/ (这里只是 Jumpserver, 没有 Web Terminal，所以访问 Web Terminal 会报错)

账号: admin 密码: admin

三. 安装 SSH Server 和 WebSocket Server: Coco
3.1 下载或 Clone 项目
新开一个终端，连接测试机
$ cd /opt
$ source /opt/py3/bin/activate
$ git clone https://github.com/jumpserver/coco.git && cd coco && git checkout master

3.2 安装依赖
$ cd /opt/coco/requirements
$ pip install -r requirements.txt

3.3 查看配置文件并运行
$ cd /opt/coco
$ cp conf_example.py conf.py
$ python run_server.py
这时需要去 Jumpserver 管理后台-会话管理-终端管理（http://192.168.244.144:8080/terminal/terminal/）接受 Coco 的注册

Coco version 1.0.0, more see https://www.jumpserver.org
Quit the server with CONTROL-C.
Starting ssh server at 0.0.0.0:2222

3.4 测试连接
$ ssh -p2222 admin@192.168.244.144
密码: admin

如果是用在 Windows 下，Xshell Terminal 登录语法如下
$ssh admin@192.168.244.144 2222
密码: admin
如果能登陆代表部署成功

四. 安装 Web Terminal 前端: Luna
Luna 已改为纯前端，需要 Nginx 来运行访问

访问（https://github.com/jumpserver/luna/releases）下载对应版本的 release 包，直接解压，不需要编译

4.1 下载并解压 Luna

$ cd /opt
$ wget https://github.com/jumpserver/luna/releases/download/v1.0.0/luna.tar.gz
$ tar xvf luna.tar.gz
$ chown -R root:root luna/
$ ls /opt/luna
...

五. 安装 Windows 支持组件
因为手动安装 guacamole 组件比较复杂，这里提供打包好的 docker 使用, 启动 guacamole

# 注意：这里一定要改写一下本机的IP地址, 否则会出错
$ apt-get remove docker docker-engine docker.io
$ apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
$ add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

## 如果网络不好可以使用阿里云镜像 
# $ curl -fsSL http://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo apt-key add -
# $ add-apt-repository "deb [arch=amd64] http://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable"
## 


$ apt-get update
$ apt-get install docker-ce
$ docker run -d \
  -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
  -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
  -e JUMPSERVER_SERVER=http://192.168.244.144:8080 \
  registry.jumpserver.org/public/guacamole:1.0.0
这里所需要注意的是 guacamole 暴露出来的端口是 8081，若与主机上其他端口冲突请自定义一下。

再次强调：修改 192.168.244.144 为自己 Jumpserver 的地址,不能使用 localhost 和 127.0.0.1 , 这时 去 Jumpserver-会话管理-终端管理 接受[Gua]开头的一个注册

六. 配置 Nginx 整合各组件
6.1 安装 Nginx 根据喜好选择安装方式和版本
$ apt-get -y install nginx

6.2 准备配置文件 修改 /etc/nginx/site-enabled/default
$ vim /etc/nginx/site-enabled/default


server {
    listen 80;

 ......  # 原有内容

    # location / {
    # 注释掉原有的 location / 内容
    # }
    # 新增如下内容
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    location /luna/ {
        try_files $uri / /index.html;
        alias /opt/luna/;
    }

    location /media/ {
        add_header Content-Encoding gzip;
        root /opt/jumpserver/data/;
    }

    location /static/ {
        root /opt/jumpserver/data/;
    }

    location /socket.io/ {
        proxy_pass       http://localhost:5000/socket.io/;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /guacamole/ {
        proxy_pass       http://192.168.244.144:8081/;
        # 请手动修改 192.168.244.144:8081 为自己 guacamole 的地址
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $http_connection;
        access_log off;
    }

    location / {
        proxy_pass http://localhost:8080;
    }

 ......  # 原有内容

}

6.3 重启 Nginx
$ nginx -t
$ service nginx restart

6.4 访问 http://192.168.244.144
