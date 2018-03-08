快速安装
==========================

Jumpserver 封装了一个 All in one Docker，可以快速启动。该镜像集成了所有需要的组件，可以使用外置 Database 和 Redis

Tips: 不建议在生产中使用


Docker 安装见: `Docker官方安装文档 <https://docs.docker.com/install/>`_


快速启动
```````````````
使用 root 命令行输入::

    $ docker run -d -p 8080:80 -p 2222:2222 registry.jumpserver.org/public/jumpserver:latest

访问
```````````````

浏览器访问: http://localhost:8080

SSH访问: ssh -p 2222 localhost


额外环境变量
```````````````

- DB_ENGINE = mysql
- DB_HOST = mysql_host
- DB_PORT = 3306
- DB_USER = xxx
- DB_PASSWORD = xxxx
- DB_NAME = jumpserver

- REDIS_HOST = ''
- REDIS_PORT = ''
- REDIS_PASSWORD = ''

 ::

   docker run -d -p 8080:80 -p 2222:2222 -e DB_ENGINE=mysql -e DB_HOST=192.168.1.1 -e DB_PORT=3306 -e DB_USER=root -e DB_PASSWORD=xxx -e DB_NAME=jumpserver  registry.jumpserver.org/public/jumpserver:latest


仓库地址
```````````````

https://github.com/jumpserver/Dockerfile
