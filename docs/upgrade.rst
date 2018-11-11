更新升级
-------------

说明
~~~~~~~
- 请先检查自己各组件的当前版本
- 不支持从 0.x 版本升级到 1.x 版本
- 本文档仅针对 1.0 及之后的版本升级教程
- 从 1.4.x 版本开始 mysql 版本需要大于等于 5.6，mariadb 版本需要大于等于 5.5.6

0. 检查数据库表结构文件是否完整

::

    # 为了保证能顺利升级，请先检查数据库表结构文件是否完整
    $ cd /opt/jumpserver/apps
    $ for d in $(ls); do if [ -d $d ] && [ -d $d/migrations ]; then ll ${d}/migrations/*.py | grep -v __init__.py; fi; done

    # 新开一个终端，连接到 jumpserver 的数据库服务器
    $ mysql -uroot -p
    > use jumpserver;
    > select app,name from django_migrations where app in('assets','audits','common','ops','orgs','perms','terminal','users') order by app asc;

    # 如果左右对比信息不一致，请勿升级，升级必然失败

1. 升级 Jumpserver（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    # 升级前请做好 jumpserver 与 数据库 备份，谨防意外，具体的备份命令可以参考离线升级
    $ cd /opt/jumpserver
    $ ./jms stop
    $ git pull

    # jumpserver 版本小于 1.3 升级到最新版本请使用新的 config.py （升级前版本小于 1.3 需要执行此步骤，否则跳过）
    $ mv config.py config.bak
    $ cp config_example.py config.py
    $ vim config.py  # 参考安装文档进行修改

    # 所有版本都需要执行此步骤
    $ pip install -r requirements/requirements.txt
    $ cd utils && sh make_migrations.sh

    # 如果执行 sh make_migrations.sh 时有红色文字提示 Run 'manage.py make_migrations' 和 'manage.py migrate' ，则需要执行下面4条命令，没有则忽略这一步
    $ cd /opt/jumpserver/apps
    $ python manage.py makemigrations
    $ python manage.py migrate
    $ cd ../utils && sh make_migrations.sh

    # 1.0.x 升级到最新版本需要执行迁移脚本 （新版本授权管理更新，升级前版本不是 1.0.x 请跳过）
    $ sh 2018_04_11_migrate_permissions.sh

    # 任意版本升级到 1.4.0 版本，需要执行（升级前版本小于 1.4.0 需要执行此步骤）
    $ sh 2018_07_15_set_win_protocol_to_ssh.sh

    # 启动 jumpserver
    $ cd ../ && ./jms start all

    # 任意版本升级到 1.4.2 版本，需要修改 nginx 配置 （升级前版本小于 1.4.2 需要执行此步骤）
    $ vim /etc/nginx/conf.d/jumpserver.conf  # 部分用户的配置文件是/etc/nginx/nginx.conf

    ...

    location /socket.io/ {
        ... 原来的内容，请参考安装文档 nginx 部分
    }

    # 加入下面内容
    location /coco/ {
        proxy_pass       http://localhost:5000/coco/;  # 如果coco安装在别的服务器，请填写它的ip
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        access_log off;
    }
    # 到此结束

    location /guacamole/ {
        ... 原来的内容，请参考安装文档 nginx 部分
    }

    ...

    # 保存后重新载入配置
    $ nginx -s reload

2. 升级 Coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    # 如果 coco 目录非默认位置请手动修改
    $ cd /opt/coco
    $ ./cocod stop
    $ git pull && pip install -r requirements/requirements.txt

    # coco 升级前版本小于 1.4.1 升级到最新版本请使用新的 conf.py （升级前版本小于 1.4.1 需要执行此步骤）
    $ mv conf.py coco.bak
    $ cp conf_example.py conf.py
    $ vim conf.py  # 参考安装文档进行修改

    $ ./cocod start

3. 升级 Luna

重新下载 release 包（https://github.com/jumpserver/luna/releases）

::

    $ cd /opt
    $ rm -rf luna
    $ wget https://github.com/jumpserver/luna/releases/download/v1.4.4/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

    # 注意把浏览器缓存刷新下

4. 升级 guacamole

::

    $ cd /opt/docker-guacamole
    $ git pull  # 如果没有代码更新，无需升级 guacamole
    $ /etc/init.d/guacd stop
    $ sh /config/tomcat8/bin/shutdown.sh
    $ tar -xf guacamole-server-0.9.14.tar.gz
    $ cd guacamole-server-0.9.14
    $ autoreconf -fi
    $ ./configure --with-init-dir=/etc/init.d
    $ make && make install
    $ cd ..
    $ rm -rf guacamole-server-0.9.14.tar.gz guacamole-server-0.9.14
    $ ldconfig
    $ cp guacamole-auth-jumpserver-0.9.14.jar /config/guacamole/extensions/guacamole-auth-jumpserver-0.9.14.jar
    $ cp root/app/guacamole/guacamole.properties /config/guacamole/
    $ cp guacamole-0.9.14.war /config/tomcat8/webapps/ROOT.war

    $ /etc/init.d/guacd start
    $ sh /config/tomcat8/bin/startup.sh

5. Docker 部署 coco guacamole 升级说明

::

    # 先到 Web 会话管理 - 终端管理 删掉所有组件
    $ docker sop jms_coco
    $ docker stop jms_guacamole
    $ docker rm jms_coco
    $ docker rm jms_guacamole
    $ docker pull docker pull wojiushixiaobai/coco:1.4.4
    $ docker pull wojiushixiaobai/guacamole:1.4.4
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> wojiushixiaobai/coco:1.4.4
    $ docker run --name jms_guacamole -d -p 8081:8081 -e JUMPSERVER_SERVER=http://<Jumpserver_url> wojiushixiaobai/guacamole:1.4.4

    # 到 Web 会话管理 - 终端管理 接受新的注册


切换分支或releases包升级
-------------------------------

说明
~~~~~~~
- 不支持从 0.x 版本升级到 1.x 版本
- 本文档仅针对 1.0 及之后的版本升级教程
- 从 1.4.x 版本开始 MySQL 版本需要大于等于 5.6，PostgreSQL 版本需要大于等于 9.4

**Jumpserver**

说明: 如果是新开的终端，别忘了 source /opt/py3/bin/activate

1. 备份 jumpserver 配置文件、数据库表结构及录像文件

::

    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ cd /opt/jumpserver
    $ cp config.py $jumpserver_backup
    $ cp -r data/media $jumpserver_backup/

    $ cd apps
    $ for d in $(ls);do
        if [ -d $d ] && [ -d $d/migrations ];then
          mkdir -p $jumpserver_backup/${d}/migrations
          cp ${d}/migrations/*.py $jumpserver_backup/${d}/migrations/
        fi
      done

2. 备份数据库，已被不时之需

::

  $ mysqldump -u你的数据库账号 -h数据库地址 -p 数据库名称 > $jumpserver_backup/db_backup.sql

3. 切换分支或下载离线包, 更新代码

::

   $ cd /opt
   $ mv jumpserver jumpserver_bak
   $ git clone https://github.com/jumpserver/jumpserver.git
   $ cd jumpserver && git checkout master  # or other branch
   $ git pull

4. 还原配置文件、数据库表结构文件及录像文件

::

   $ cd /opt/jumpserver
   $ cp $jumpserver_backup/config.py .
   $ cp -r $jumpserver_backup/media/* data/media/

   $ cd $jumpserver_backup/
   $ for d in $(ls);do
       if [ -d $d ] && [ -d $d/migrations ];then
         cp ${d}/migrations/*.py /opt/jumpserver/apps/${d}/migrations/
       fi
     done

5. 更新依赖或表结构

::

   $ cd /opt/jumpserver
   $ pip install -r requirements/requirements.txt
   $ cd utils && sh make_migrations.sh


**Coco**

说明: 以下操作都在 coco 项目所在目录

coco 是无状态的，备份 keys 目录即可

1. 备份配置文件及 keys

::

   $ cd /opt/coco
   $ cp conf.py $jumpserver_backup/
   $ cp -r keys $jumpserver_backup/


2. 离线更新升级 coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

   $ cd /opt
   $ mv coco coco_bak
   $ git clone https://github.com/jumpserver/coco.git
   $ cd coco && git checkout master  # or other branch
   $ git pull

3. 还原 keys 目录

::

   $ cd /opt/coco
   $ cp $jumpserver_backup/conf.py .
   $ cp -r $jumpserver_backup/keys .

4. 升级依赖

::

   $ git pull &&  pip install -r requirements/requirements.txt


**Luna**

直接下载最新 Release 包替换即可


**Guacamole**

直接参考上面的升级即可
