快速安装
==========================

Jumpserver 封装了一个All in one Docker，可以快速启动。该镜像集成了所有需要的组件，可以使用外置db和redis

Tips: 不建议在生产中使用


Docker 安装见: `Docker官方安装文档 <https://docs.docker.com/install/>`_


快速启动
```````````````
使用root命令行输入::

    $ docker run -p 8080:80 -p 2222:2222 jumpserver/jumpserver:0.5.0-beta2

访问
```````````````

浏览器访问: http://localhost:8080

ssh访问: ssh -p 2222 localhost