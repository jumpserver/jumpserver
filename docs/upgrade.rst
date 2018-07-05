更新升级
-------------

1. 升级 Jumpserver（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    # 升级前请做好 jumpserver 与 数据库 备份，谨防意外，具体的备份命令可以参考离线升级
    $ cd /opt/jumpserver
    $ git pull
    $ pip install -r requirements/requirements.txt  # 如果使用其他源下载失败可以使用 -i 参数指定源
    $ cd utils && sh make_migrations.sh

    # 1.0.x 升级 1.2.0及以后的版本 需要执行迁移脚本（新版本授权管理更新）
    $ sh 2018_04_11_migrate_permissions.sh
 
2. 升级 Coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    # 如果 coco 目录非默认位置请手动修改
    $ cd /opt/coco
    $ git pull && pip install -r requirements/requirements.txt

    # 如果使用其他源下载失败可以使用 -i 参数指定源
    $ pip install -r requirements/requirements.txt -i https://pypi.org/simple

3. 升级 Luna

重新下载 release 包（https://github.com/jumpserver/luna/releases）

::

    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.3.2/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

4. 升级 guacamole

::

    $ docker pull registry.jumpserver.org/public/guacamole:latest
    $ docker stop jms_guacamole  # 或者写guacamole的容器ID
    $ docker rename jms_guacamole jms_guacamole_bak  # 如果名称不正确请手动修改
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写Jumpserver的url地址> \
      registry.jumpserver.org/public/guacamole:latest

    # 确定升级完成后，可以删除备份容器
    $ docker rm jms_guacamole_bak


切换分支或离线升级
-------------------------------


**Jumpserver**

说明: 如果是新开的终端，别忘了 source /opt/py3/bin/activate

1. 备份jumpserver配置文件、数据库表结构及录像文件

::

    $ jumpserver_backup=/tmp/jumpserver_backup
    $ mkdir -p $jumpserver_backup
    $ cd /opt/jumpserver
    $ cp config.py $jumpserver_backup
    $ cp -r data/media $jumpserver_backup/

    $ for app in audits common users assets ops perms terminal;do
        mkdir -p $jumpserver_backup/${app}_migrations
        cp apps/${app}/migrations/*.py $jumpserver_backup/${app}_migrations
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
   $ for app in audits common users assets ops perms terminal;do
       cp $jumpserver_backup/${app}_migrations/*.py apps/${app}/migrations/
     done

   $ cp $jumpserver_backup/config.py .
   $ cp -r $jumpserver_backup/media/* data/media/

5. 更新依赖或表结构

::

   $ pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh


**Coco**

说明: 以下操作都在 coco 项目所在目录

coco是无状态的，备份 keys 目录即可

1. 备份配置文件及keys

::

   $ cd /opt/coco
   $ cp conf.py $jumpserver_backup/
   $ cp -r keys $jumpserver_backup/


2. 离线更新升级coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

   $ cd /opt
   $ mv coco coco_bak
   $ git clone https://github.com/jumpserver/coco.git
   $ cd coco && git checkout master  # or other branch
   $ git pull

3. 还原 keys目录

::

   $ cd /opt/coco
   $ cp $jumpserver_backup/conf.py .
   $ cp -r $jumpserver_backup/keys .

4. 升级依赖

::

   $ git pull && cd requirements && pip install -r requirements.txt


**Luna**

直接下载最新Release包替换即可


**Guacamole**

直接参考上面的升级即可, 需要注意的是如果更换机器，请备份
