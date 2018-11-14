更新升级
-------------

1.0.x 升级到 1.4.4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 请先检查自己各组件的当前版本
- 不支持从 0.x 版本升级到 1.x 版本
- 本文档仅针对 1.0 及之后的版本升级教程
- 从 1.4.x 版本开始 mysql 版本需要大于等于 5.6,mariadb 版本需要大于等于 5.5.6

0. 检查数据库表结构文件是否完整

.. code-block:: shell

    # 为了保证能顺利升级,请先检查数据库表结构文件是否完整
    $ cd /opt/jumpserver/apps
    $ for d in $(ls); do if [ -d $d ] && [ -d $d/migrations ]; then ll ${d}/migrations/*.py | grep -v __init__.py; fi; done

    # 新开一个终端,连接到 jumpserver 的数据库服务器
    $ mysql -uroot -p
    > use jumpserver;
    > select app,name from django_migrations where app in('assets','audits','common','ops','orgs','perms','terminal','users') order by app asc;

    # 如果左右对比信息不一致,请勿升级,升级必然失败

1. 备份 Jumpserver 数据库表结构 (通过releases包升级需要还原这些文件)

.. code-block:: shell

    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ cd /opt/jumpserver/apps
    $ for d in $(ls);do
        if [ -d $d ] && [ -d $d/migrations ];then
          mkdir -p $jumpserver_backup/${d}/migrations
          cp ${d}/migrations/*.py $jumpserver_backup/${d}/migrations/
        fi
      done

.. code-block:: shell

    # 还原代码 (通过releases包升级需要还原这些文件,通过git pull升级不需要执行)
    $ cd $jumpserver_backup/
    $ for d in $(ls);do
        if [ -d $d ] && [ -d $d/migrations ];then
          cp ${d}/migrations/*.py /opt/jumpserver/apps/${d}/migrations/
        fi
      done

2. 升级 Jumpserver

.. code-block:: shell

    # 升级前请做好 jumpserver 与 数据库 备份,谨防意外,具体的备份命令可以参考离线升级
    $ cd /opt/jumpserver
    $ source /opt/py3/bin/activate
    $ git pull
    $ ./jms stop

.. code-block:: shell

    # jumpserver 版本小于 1.3 升级到最新版本请使用新的 config.py (升级前版本小于 1.3 需要执行此步骤,否则跳过)
    $ mv config.py config.bak
    $ cp config_example.py config.py
    $ vi config.py  # 参考安装文档进行修改

.. code-block:: shell

    # 所有版本都需要执行此步骤
    $ pip install -r requirements/requirements.txt
    $ cd utils && sh make_migrations.sh

.. code-block:: shell

    # 如果执行 sh make_migrations.sh 时有红色文字提示 Run 'manage.py make_migrations' 和 'manage.py migrate' ,则需要执行下面4条命令,没有则忽略这一步
    $ cd /opt/jumpserver/apps
    $ python manage.py makemigrations
    $ python manage.py migrate
    $ cd ../utils && sh make_migrations.sh

.. code-block:: shell

    # 1.0.x 升级到最新版本需要执行迁移脚本 (新版本授权管理更新,升级前版本不是 1.0.x 请跳过)
    $ sh 2018_04_11_migrate_permissions.sh

.. code-block:: shell

    # 任意版本升级到 1.4.0 版本,需要执行(升级前版本小于 1.4.0 需要执行此步骤)
    $ sh 2018_07_15_set_win_protocol_to_ssh.sh

.. code-block:: shell

    # 启动 jumpserver
    $ cd ../
    $ ./jms start all

.. code-block:: nginx

    # 任意版本升级到 1.4.2 版本,需要修改 nginx 配置 (升级前版本小于 1.4.2 需要执行此步骤)
    $ vi /etc/nginx/conf.d/jumpserver.conf  # 部分用户的配置文件是/etc/nginx/nginx.conf

    ...

    location /socket.io/ {
        # 原来的内容,请参考安装文档 nginx 部分
    }

    # 加入下面内容
    location /coco/ {
        proxy_pass       http://localhost:5000/coco/;  # 如果coco安装在别的服务器,请填写它的ip
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        access_log off;
    }
    # 到此结束

    location /guacamole/ {
        # 原来的内容,请参考安装文档 nginx 部分
    }

    ...

.. code-block:: shell

    # 保存后重新载入配置
    $ nginx -s reload

3. 升级 Coco (docker 部署的请忽略往下看)

.. code-block:: shell

    # 如果 coco 目录非默认位置请手动修改
    $ cd /opt/coco
    $ source /opt/py3/bin/activate
    $ git pull
    $ ./cocod stop
    $ pip install -r requirements/requirements.txt

.. code-block:: shell

    # coco 升级前版本小于 1.4.1 升级到最新版本请使用新的 conf.py (升级前版本小于 1.4.1 需要执行此步骤)
    $ mv conf.py coco.bak
    $ cp conf_example.py conf.py
    $ vi conf.py  # 参考安装文档进行修改

    $ ./cocod start

4. 升级 guacamole (docker 部署的请忽略往下看)

.. code-block:: shell

    $ cd /opt/docker-guacamole
    $ git pull
    $ /etc/init.d/guacd stop
    $ sh /config/tomcat8/bin/shutdown.sh
    $ cp guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar

    $ cd /config
    $ wget https://github.com/ibuler/ssh-forward/releases/download/v0.0.5/linux-amd64.tar.gz
    $ tar xf linux-amd64.tar.gz -C /bin/
    $ chmod +x /bin/ssh-forward

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

5. 升级 Luna

重新下载 release 包(https://github.com/jumpserver/luna/releases)

.. code-block:: shell

    $ cd /opt
    $ rm -rf luna
    $ wget https://github.com/jumpserver/luna/releases/download/v1.4.4/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

    # 注意把浏览器缓存刷新下

6. Docker 部署 coco guacamole 升级说明

.. code-block:: shell

    # 先到 Web 会话管理 - 终端管理 删掉所有组件
    $ docker sop jms_coco
    $ docker stop jms_guacamole
    $ docker rm jms_coco
    $ docker rm jms_guacamole
    $ docker pull wojiushixiaobai/coco:1.4.4
    $ docker pull wojiushixiaobai/guacamole:1.4.4
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> wojiushixiaobai/coco:1.4.4
    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> wojiushixiaobai/guacamole:1.4.4

    # 到 Web 会话管理 - 终端管理 接受新的注册


1.4.4 升级到 1.4.5 (下个版本,当前还未开放,请勿执行)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 当前版本必须是 1.4.4 版本,否则请先升级到 1.4.4
- 从 1.4.5 版本开始,由官方维护唯一 migrations

**Jumpserver**

.. code-block:: shell

    $ cd /opt/jumpserver
    $ git pull
    $ source /opt/py3/bin/activate
    $ ./jms stop
    $ git pull

    $ pip install -r requirements/requirements.txt

    $ cd utils
    $ sh 1.4.4_to_1.4.5_migrations.sh
    $ sh make_migrations.sh

    $ cd ../
    $ ./jms start all

**Coco**

说明: Docker 部署的请跳过

.. code-block:: shell

    $ cd /opt/coco
    $ git pull
    $ source /opt/py3/bin/activate
    $ ./cocod stop
    $ pip install -r requirements/requirements.txt
    $ ./cocod start

**Guacamole**

说明: Docker 部署的请跳过

.. code-block:: shell

    $ cd /opt/docker-guacamole
    $ git pull
    $ /etc/init.d/guacd stop
    $ sh /config/tomcat8/bin/shutdown.sh
    $ cp guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar

    $ cd /config
    $ wget https://github.com/ibuler/ssh-forward/releases/download/v0.0.5/linux-amd64.tar.gz
    $ tar xf linux-amd64.tar.gz -C /bin/
    $ chmod +x /bin/ssh-forward

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

**Luna**

说明: 直接下载 release 包

.. code-block:: shell

    $ cd /opt
    $ rm -rf luna
    $ wget https://github.com/jumpserver/luna/releases/download/v1.4.5/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

**Docker Coco Guacamole**

说明: Docker 部署的 coco 与 guacamole 升级说明

.. code-block:: shell

    # 先到 Web 会话管理 - 终端管理 删掉所有组件
    $ docker sop jms_coco
    $ docker stop jms_guacamole
    $ docker rm jms_coco
    $ docker rm jms_guacamole
    $ docker pull wojiushixiaobai/coco:1.4.5
    $ docker pull wojiushixiaobai/guacamole:1.4.5
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> wojiushixiaobai/coco:1.4.5
    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> wojiushixiaobai/guacamole:1.4.5

    # 到 Web 会话管理 - 终端管理 接受新的注册
