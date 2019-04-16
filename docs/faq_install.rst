安装过程中常见的问题
----------------------------

1. git clone 提示 ssl 错误

.. code-block:: vim

    # 一般是由于时间不同步, 或者网络有问题导致的
    # 可以尝试下载 releases 包

2. pip install 提示 ssl 错误

.. code-block:: vim

    # 参考第一条解决

3. pip install 提示 download 错误

.. code-block:: vim

    # 一般是由于网络不好, 导致下载文件失败, 重新执行命令即可
    # 如果多次重试均无效, 请更换网络环境

4. pip install 提示 Could not find a version that satisfies the requirement xxxxxx==x.x.xx(版本)

.. code-block:: shell

    # 一般是由于镜像源未同步, -i 指定官方源即可, 如：
    $ pip install -r requirement.txt -i https://pypi.org/simple
    $ pip install xxxxx==x.x.xx -i https://pypi.org/simple

5. pip install 提示 install for mysqlclient ... error /usr/bin/ld: 找不到 -lmariadb

.. code-block:: shell

    # 如果是 Mariadb 大于 10 版本
    $ yum install MariaDB-shared

6. sh make_migrations.sh 时报错 from config import config as CONFIG File "/opt/jumpserver/config.yml", line 38

.. code-block:: vim

    # 这是由于 config.yml 里面的内容格式不对, 请参考安装文档的说明, 把提示的内容与上一行对齐即可

7. sh make_migrations.sh 时报错 Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?

.. code-block:: shell

    # 一般是由于 py3 环境未载入
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功, 以后运行 Jumpserver 都要先运行以上 source 命令, 以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 如果已经在 py3 虚拟环境下, 任然报 Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?
    $ cd /opt/jumpserver/requirements
    $ pip install -r requirements.txt
    # 然后重新执行 sh make_migrations.sh

8.  sh make_migrations.sh 报错 CommandError: Conflicting migrations detected; multiple ... django_celery_beat ...

.. code-block:: shell

    # 这是由于 django-celery-beat老版本有bug引起的
    $ rm -rf /opt/py3/lib/python3.6/site-packages/django_celery_beat/migrations/
    $ pip uninstall django-celery-beat
    $ pip install django-celery-beat

9. 执行 ./jms start all 后一直卡在 beat: Waking up in 1.00 minute.

.. code-block:: vim

    # 如果没有error提示进程无法启动, 那么这是正常现象
    # 如果不想在前台启动, 可以使用 ./jms start all -d 在后台启动

10. 执行 ./jms start all 后提示 xxx is stopped

.. code-block:: shell

    # Error: xxx start error
    # xxx is stopped
    $ ./jms restart xxx  # 如 ./jms restart gunicorn

11. 执行 ./jms start all 后提示 WARNINGS: ?: (mysql.W002) MySQL Strict Mode is not set for database connection 'default' ...

.. code-block:: vim

    # 这是严格模式的警告, 可以参考后面的url解决, 或者忽略

12. 启动 Jumpserver 或者 coco 报错 Error: expected '<document start>', but found '<scalar>'

.. code-block:: vim

    # 这是因为你的 config.yml 文件格式有误
    # 常见的错误就是字段为空或者: 后面有一个空格
    # SECRET_KEY: xxxxx  # 不要忽略: 后面的空格

13. 启动 jumpserver 后, 访问 8080 端口页面显示不正常

.. code-block:: vim

    # 这是因为你在 config.yml 里面设置了 DEBUG: false
    # 跟着教程继续操作, 后面搭建 nginx 代理即可正常访问

14. 执行 ./cocod start 后提示 No module named 'jms'

.. code-block:: shell

    # 一般是由于 py3 环境未载入
    $ source /opt/py3/bin/activate

    # 看到下面的提示符代表成功, 以后运行 Jumpserver 都要先运行以上 source 命令, 以下所有命令均在该虚拟环境中运行
    (py3) [root@localhost py3]

    # 如果已经在 py3 虚拟环境下
    $ cd /opt/coco/
    $ pip install -r requirements/requirements.txt
    # 然后重新执行 ./cocod start 即可

15. 执行 ./cocod start 后提示 Failed register terminal xxxx exist already

.. code-block:: shell

    # 这是由于 coco 注册未成功造成的, 需要重新注册 (能正常访问 jumpserver 页面后再处理)
    # 到 Jumpserver后台 会话管理-终端管理  删掉 coco 的注册
    # 必须到 Jumpserver后台 会话管理-终端管理  删掉 coco 的注册
    # 一定要先到 Jumpserver后台 会话管理-终端管理  删掉 coco 的注册
    $ cd /opt/coco && ./cocod stop
    $ rm /opt/coco/data/keys/.access_key  # coco, 如果你是按文档安装的, key应该在这里, 如果不存在key文件直接下一步
    $ ./cocod start -d  # 正常运行后到Jumpserver 会话管理-终端管理 里面接受coco注册

16. 执行 ./cocod start 后提示 Failed register terminal unknow: xxxx

.. code-block:: vim

    # 这是因为当前系统的 hostname 有 coco 不支持的字符, 需要手动指定 coco 的 NAME
    $ cd /opt/coco/
    $ vi config.yml

    # 项目名称, 会用来向Jumpserver注册, 识别而已, 不能重复
    # NAME: {{ Hostname }}
    NAME: localhost

    # 保存后重新执行 ./cocod start 即可

17. 运行 ./cocod start 后提示 "detail":"身份认证信息未提供。" Failed register terminal

.. code-block:: shell

    # 保证 coco 的 BOOTSTRAP_TOKEN 与 jumpserver/config.yml 里面的内容不一致
    $ cat /opt/jumpserver/config.yml | grep BOOTSTRAP_TOKEN
    $ cat /opt/coco/config.yml | grep BOOTSTRAP_TOKEN

    # 修改成一致保存后 重新执行 ./cocod start 即可

18. 运行 ./cocod start 后提示 Connect endpoint http://xxxx:8080 error: HTTPConnectionPool(host='xxxx', port=8080)

.. code-block:: vim

    # 这是因为 coco 无法连接到 jumpserver 报的错误, 确定 http://xxxx:8080 设置正确(配置文件 coco/config.yml)
    # 如果 jumpserver 的IP和端口不对, 请手动修改 config.yml 的 CORE_HOST

19. 运行 ./cocod start 后提示 Unexpected error occur: 'AppService' object has no attribute 'get_system_user_cmd_filter_rules'

.. code-block:: vim

    # 这是因为你的 pip 依赖包未正确安装, 参考本文档第 4 条

20. 通过 nginx 代理的端口访问 jumpserver 页面显示不正常

.. code-block:: nginx

    # 这是因为你没有按照教程进行安装, 修改了安装目录, 需要在 nginx 的配置文件里面修改资源路径
    $ vi /etc/nginx/conf.d/jumpserver.conf

    ...

    server {
        listen 80;  # 代理端口, 以后将通过此端口进行访问, 不再通过8080端口

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;  # luna 路径, 如果修改安装目录, 此处需要修改
        }

        location /media/ {
            add_header Content-Encoding gzip;
            root /opt/jumpserver/data/;  # 录像位置, 如果修改安装目录, 此处需要修改
        }

        location /static/ {
            root /opt/jumpserver/data/;  # 静态资源, 如果修改安装目录, 此处需要修改
        }

        location /socket.io/ {
            proxy_pass       http://localhost:5000/socket.io/;  # 如果coco安装在别的服务器, 请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /coco/ {
            proxy_pass       http://localhost:5000/coco/;  # 如果coco安装在别的服务器, 请填写它的ip
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /guacamole/ {
            proxy_pass       http://localhost:8081/;  # 如果guacamole安装在别的服务器, 请填写它的ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
            client_max_body_size 100m;  # Windows 文件上传大小限制
        }

        location / {
            proxy_pass http://localhost:8080;  # 如果jumpserver安装在别的服务器, 请填写它的ip
        }
    }

    ...

21. 访问 luna 页面提示 Luna是单独部署的一个程序, 你需要部署luna, coco, 配置nginx做url分发...

.. code-block:: vim

    # 请通过 nginx 代理的端口访问 jumpserver 页面, 不要再直接访问 8080 端口
