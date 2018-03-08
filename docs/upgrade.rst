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