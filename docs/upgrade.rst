升级
----

1. 升级 jumpserver

::

    $ git pull && pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh

2. 升级 coco

::

    $ git pull && cd requirements && pip install -r requirements.txt   # 不要指定 -i参数

3. 升级 luna

重新下载release包