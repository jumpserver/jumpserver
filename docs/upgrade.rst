在线更新升级
-------------

说明
~~~~~~~
- 不支持从 0.x 版本升级到 1.x 版本
- 本文档仅针对 1.0 及之后的版本升级教程

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
    $ git pull

    # jumpserver 版本小于 1.3 升级到最新版本请使用新的 config.py
    $ mv config.py config.bak
    $ cp config_example.py config.py
    $ vim config.py  # 参考安装文档进行修改

    $ pip install -r requirements/requirements.txt -i https://pypi.python.org/simple
    $ cd utils && sh make_migrations.sh

    # 1.0.x 升级到最新版本需要执行迁移脚本（新版本授权管理更新）
    $ sh 2018_04_11_migrate_permissions.sh

    # 任意版本升级到 1.4.0 版本，需要执行
    $ sh 2018_07_15_set_win_protocol_to_ssh.sh

    # 如果执行 sh make_migrations.sh 时有红色提示 Run 'manage.py make_migrations' 和 'manage.py migrate'
    $ cd /opt/jumpserver/apps
    $ python manage.py makemigrations
    $ python manage.py migrate
    $ cd ../utils && sh make_migrations.sh
 
2. 升级 Coco（如果是新开的终端，别忘了 source /opt/py3/bin/activate）

::

    # 如果 coco 目录非默认位置请手动修改
    $ cd /opt/coco
    $ git pull && pip install -r requirements/requirements.txt -i https://pypi.python.org/simple

    # coco 版本小于 1.4.1 升级到最新版本请使用新的 conf.py
    $ mv conf.py coco.bak
    $ cp conf_example.py conf.py
    $ vim conf.py  # 参考安装文档进行修改

3. 升级 Luna

重新下载 release 包（https://github.com/jumpserver/luna/releases）

::

    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.4.1/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

4. 升级 guacamole

::

    $ docker pull jumpserver/guacamole:latest
    # 如果镜像不是 jumpserver/guacamole，请修改成 registry.jumpserver.org/public/guacamole
    $ docker stop jms_guacamole  # 或者写guacamole的容器ID
    $ docker rename jms_guacamole jms_guacamole_bak  # 如果名称不正确请手动修改
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写Jumpserver的url地址> \
      jumpserver/guacamole:latest

    # 确定升级完成后，可以删除备份容器
    $ docker rm jms_guacamole_bak


切换分支或离线升级
-------------------------------

说明
~~~~~~~
- 不支持从 0.x 版本升级到 1.x 版本
- 本文档仅针对 1.0 及之后的版本升级教程

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
   $ pip install -r requirements/requirements.txt -i https://pypi.python.org/simple
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

   $ git pull &&  pip install -r requirements/requirements.txt -i https://pypi.python.org/simple


**Luna**

直接下载最新 Release 包替换即可


**Guacamole**

直接参考上面的升级即可, 需要注意的是如果更换机器，请备份
