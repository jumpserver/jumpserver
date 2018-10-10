安装过程中常见的问题
----------------------------

1. git clone 提示 ssl 错误

::

    一般是由于时间不同步，或者网络有问题导致的
    可以尝试下载 releases 包

2. pip install 提示 ssl 错误

::

    参考第一条解决

3. pip install 提示 download 错误

::

    一般是由于网络不好，导致下载文件失败，重新执行命令即可
    如果多次重试均无效，请更换网络环境

4. bash make_migrations.sh 时报错 from config import config as CONFIG File "/opt/jumpserver/config.py", line 38

::

    这是由于 config.py 里面的内容格式不对，请参考安装文档的说明，把提示的内容与上一行对齐即可

5. bash make_migrations.sh 时报错 Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?

::

    # 一般是由于 py3 环境未载入
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 如果已经在 py3 虚拟环境下，任然报 Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?
    $ cd /opt/jumpserver/requirements
    $ pip install -r requirements.txt
    # 然后重新执行 bash make_migrations.sh

6.  sh make_migrations.sh 报错 CommandError: Conflicting migrations detected; multiple ... django_celery_beat ...

::

    # 这是由于 django-celery-beat老版本有bug引起的
    $ rm -rf /opt/py3/lib/python3.6/site-packages/django_celery_beat/migrations/
    $ pip uninstall django-celery-beat
    $ pip install django-celery-beat

7. 执行 ./jms start all 后一直卡在 beat: Waking up in 1.00 minute.

::

    如果没有error提示进程无法启动，那么这是正常现象
    如果不想在前台启动，可以使用 ./jms start all -d 在后台启动

8. 执行 ./jms start all 后提示 xxx is stopped

::

    # Error: xxx start error
    # xxx is stopped
    $ ./jms restart xxx  # 如 ./jms restart gunicorn

9. 执行 ./jms start all 后提示 WARNINGS: ?: (mysql.W002) MySQL Strict Mode is not set for database connection 'default' ...

::

    这是严格模式的警告，可以参考后面的url解决，或者忽略

10. 启动 jumpserver 后，访问 8080 端口页面显示不正常

::

    这是因为你在 config.py 里面设置了 DEBUG = False
    跟着教程继续操作，后面搭建 nginx 代理即可正常访问

11. 执行 ./cocod start 后提示 No module named 'jms'

::

    # 一般是由于 py3 环境未载入
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功，以后运行 Jumpserver 都要先运行以上 source 命令，以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 如果已经在 py3 虚拟环境下
    $ cd /opt/coco/
    $ pip install -r requirements/requirements.txt
    # 然后重新执行 ./cocod start 即可

12. 执行 ./cocod start 后提示 Failed register terminal xxxx exist already

::

    # 这是由于 coco 注册未成功造成的，需要重新注册 (能正常访问 jumpserver 页面后再处理)
    # 到 Jumpserver后台 会话管理-终端管理  删掉 coco 的注册
    $ cd /opt/coco && ./cocod stop
    $ rm /opt/coco/keys/.access_key  # coco, 如果你是按文档安装的，key应该在这里，如果不存在key文件直接下一步
    $ ./cocod start -d  # 正常运行后到Jumpserver 会话管理-终端管理 里面接受coco注册

13. 执行 ./cocod start 后提示 Failed register terminal unknow: xxxx

::

    # 这是因为当前系统的 hostname 有 coco 不支持的字符，需要手动指定 coco 的 NAME
    $ cd /opt/coco/
    $ vim conf.py

    # 项目名称, 会用来向Jumpserver注册, 识别而已, 不能重复
    # NAME = "localhost"
    NAME = "coco"

    # 保存后重新执行 ./cocod start 即可

14. 运行 ./cocod start 后提示 No such file or directory: '/opt/coco/keys/.access_key'

::

    # 这是一个小 bug，之后的版本会修复掉
    $ cd /opt/coco
    $ mkdir keys

    # 保存后重新执行 ./cocod start 即可

15. 通过 nginx 代理的端口访问 jumpserver 页面显示不正常

::

    # 这是因为你没有按照教程进行安装，修改了安装目录，需要在 nginx 的配置文件里面修改资源路径
    $ vim /etc/nginx/nginx.conf

    ...

    server {
        listen 80;  # 代理端口，以后将通过此端口进行访问，不再通过8080端口

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;  # luna 路径，如果修改安装目录，此处需要修改
        }

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;  # 录像位置，如果修改安装目录，此处需要修改
        }

        location /static/ {
            root /opt/jumpserver/data/;  # 静态资源，如果修改安装目录，此处需要修改
        }

        location /socket.io/ {
            proxy_pass       http://localhost:5000/socket.io/;  # 如果coco安装在别的服务器，请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /guacamole/ {
            proxy_pass       http://localhost:8081/;  # 如果guacamole安装在别的服务器，请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
            client_max_body_size 100m;  # Windows 文件上传大小限制
        }

        location / {
            proxy_pass http://localhost:8080;  # 如果jumpserver安装在别的服务器，请填写它的ip
        }
    }

    ...

16. 访问 luna 页面提示 Luna是单独部署的一个程序，你需要部署luna，coco，配置nginx做url分发...

::

    请通过 nginx 代理的端口访问 jumpserver 页面，不要再直接访问 8080 端口
