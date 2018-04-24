更新升级
-------------

1. 升级 Jumpserver（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    $ git pull && pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh

    # 1.0.x 升级 1.2.0 需要执行迁移脚本（新版本授权管理更新）
    $ sh 2018_04_11_migrate_permissions.sh
 
2. 升级 Coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    $ git pull && pip install -r requirements/requirements.txt   # 不要指定 -i参数

3. 升级 Luna

重新下载 release 包（https://github.com/jumpserver/luna/releases）

4. 升级 guacamole

::

    $ docker pull registry.jumpserver.org/public/guacamole:latest
    $ docker stop jms_guacamole  # 或者写guacamole的容器ID
    $ docker rename jms_guacamole jms_guacamole_bak  # 如果名称不正确请手动修改
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写Jumpserver服务器的IP地址>:8080 \
      registry.jumpserver.org/public/guacamole:latest

    # 确定升级完成后，可以删除备份容器
    $ docker rm jms_guacamole_bak


切换分支或离线升级
-------------------------------


**Jumpserver**

说明: 如果是新开的终端，别忘了 source /opt/py3/bin/activate

1. 备份jumpserver

::

    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ cd /opt/jumpservrer
    $ cp -r ./ $jumpserver_backup

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

4. 还原录像文件

::

   $ cp -r $jumpserver_backup/media/* data/media/

5. 更新依赖或表结构

::

   $ pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh


**Coco**

说明: 以下操作都在 coco 项目所在目录

coco是无状态的，备份 keys 目录即可

1. 备份keys

::

   $ cp -r keys $jumpserver_backup/


2. 离线更新升级coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

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
