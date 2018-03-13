升级
----

1. 升级 Jumpserver

::

    $ git pull && pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh

2. 升级 Coco

::

    $ git pull && cd requirements && pip install -r requirements.txt   # 不要指定 -i参数

3. 升级 Luna

重新下载 release 包（https://github.com/jumpserver/luna/releases）

4. 升级 guacamole

:: 

    $ docker pull registry.jumpserver.org/public/guacamole:latest
    $ docker stop <guacamole>
    $ docker run -d \
      -p 8081:8080 \
      -e JUMPSERVER_SERVER=http://<填写本机的IP地址>:8080 \
      registry.jumpserver.org/public/guacamole:latest
