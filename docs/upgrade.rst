更新升级
-------------

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
    $ docker stop jms_guacamole  # 或者写guacamole的容器ID
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写本机的IP地址>:8080 \
      registry.jumpserver.org/public/guacamole:latest


切换分支或离线升级
-------------------------------


**Jumpserver**

说明: 以下操作，都在jumpserver所在目录运行

1. 备份配置文件

::

    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ cp config.py $jumpserver_backup

2. 备份migrations migrations中存的是数据库表结构的变更，切换分支会丢失

::

   $ for app in common users assets ops perms terminal;do
      mkdir -p $jumpserver_backup/${app}_migrations
      cp apps/${app}/migrations/*.py $jumpserver_backup/${app}_migrations
   done


3. 备份数据库，已被不时之需

::

  $ mysqldump -u你的数据库账号 -h数据库地址 -p 数据库名称 > $jumpserver_backup/db_backup.sql

4. 备份录像文件

::

   $ cp -r data/media $jumpserver_backup/

5. 切换分支或下载离线包, 更新代码

::

   $ git checkout master  # or other branch


6. 还原配置文件

::

   $ cp $jumpserver_backup/config.py .

7. 还原数据库表结构记录

::

   $ for app in common users assets ops perms terminal;do
      cp $jumpserver_backup/${app}_migrations/*.py ${app}/migrations/
   done

8. 还原录像文件

::

   $ cp -r $jumpserver_backup/media/* data/media/

9. 更新依赖或表结构

::
   $ pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh


**Coco**

说明: 以下操作都在 coco 项目所在目录

coco是无状态的，备份 keys 目录即可

1. 备份keys

::

   $ cp -r keys $jumpserver_backup/


2. 离线更新升级coco

3. 还原 keys目录

::

   $ mv keys keys_backup
   $ cp -r  $jumpserver_backup/keys .

4. 升级依赖

::

   $ git pull && cd requirements && pip install -r requirements.txt


**Luna**

直接下载最新Release包替换即可


**Guacamole**

直接参考上面的升级即可, 需要注意的是如果更换机器，请备份


