安装后优化文档
--------------------------------

- 能解决部分CPU和内存高占用问题

配置文件调整
~~~~~~~~~~~~~~

.. code-block:: shell

    $ cd /opt/jumpserver
    $ vi config.yml

    # 调整 debug 模式和 log_level
    ...
    DEBUG: false
    ...
    LOG_LEVEL: ERROR
    ...

.. code-block:: shell

    $ cd /opt/coco
    $ vi config.yml

    # 调整 log_level
    ...
    LOG_LEVEL: ERROR
    ...

    # 设置好后重启 jumpserver 和 coco

静态资源 OSS 加速访问
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    # 先把静态资源上传或同步到 OSS, 如果使用其他工具上传, 注意设置文件 HTTP 头
    # 静态文件夹包括 jumpserver/data/static 和 luna
    # Bucket ACL 设置为 公共读
    # 防盗链需要添加 Jumpserver域名 和 ossEndPoint域名
    # 跨域设置需要添加 Jumpserver域名 和 ossEndPoint域名

    # 在最前端的 nginx 代理服务器上进行设置
    $ cd /etc/nginx
    $ vi conf.d/jumpserver.conf

.. code-block:: nginx

    ...
    # 根据自己的 OSS 所在地域和 域名, 自行替换 yourBucket 和 yourEndPoint
    location /static/ {
                rewrite ^/static/(.*)$ https://yourBucket.oss-cn-yourEndPoint.aliyuncs.com/static/$1 permanent;
                add_header Access-Control-Allow-Origin 'https://yourBucket.oss-cn-yourEndPoint.aliyuncs.com';
                access_log off;
    }

    location ~ /luna/.*\.(svg|eot|ico|woff|woff2|ttf|js|css|png|json|txt)$ {
                rewrite ^/luna/(.*)$ https://yourBucket.oss-cn-yourEndPoint.aliyuncs.com/luna/$1 permanent;
                add_header Access-Control-Allow-Origin 'https://yourBucket.oss-cn-yourEndPoint.aliyuncs.com';
                access_log off;
    }

.. code-block:: shell

    # 设置完成后重启 nginx
    $ nginx -s reload
