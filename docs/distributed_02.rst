分布式部署文档 - nginx 代理部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.100

+----------+------------+-----------------+---------------+------------------------+
| Protocol | ServerName |        IP       |      Port     |         Used By        |
+==========+============+=================+===============+========================+
|    TCP   |    Nginx   | 192.168.100.100 | 80, 443, 2222 |           All          |
+----------+------------+-----------------+---------------+------------------------+

开始安装
~~~~~~~~~~~~

.. code-block:: shell

    # 升级系统
    $ yum upgrade -y

    # 获取 epel-release 源
    $ yum -y install epel-release

    # 设置防火墙, 开放 80 443 2222 端口
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent
    $ firewall-cmd --zone=public --add-port=443/tcp --permanent
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent
    $ firewall-cmd --reload

    # 设置 http 访问权限
    $ setsebool -P httpd_can_network_connect 1
    $ semanage port -a -t http_port_t -p tcp 2222

.. code-block:: shell

    # 安装 nginx
    $ vi /etc/yum.repos.d/nginx.repo

    [nginx]
    name=nginx repo
    baseurl=http://nginx.org/packages/centos/7/$basearch/
    gpgcheck=0
    enabled=1

    # 非 Centos7 请参考 http://nginx.org/en/linux_packages.html#stable

.. code-block:: shell

    $ yum -y install nginx
    $ systemctl enable nginx

    # 下载 luna
    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.4.9/luna.tar.gz

    # 如果网络有问题导致下载无法完成可以使用下面地址
    $ wget https://demo.jumpserver.org/download/luna/1.4.9/luna.tar.gz

    $ tar xf luna.tar.gz
    $ chown -R root:root luna

.. code-block:: nginx

    # 配置 Nginx
    $ vi /etc/nginx/nginx.conf

    user  nginx;
    worker_processes  auto;

    error_log  /var/log/nginx/error.log warn;
    pid        /var/run/nginx.pid;


    events {
        worker_connections  1024;
    }

    stream {
        log_format  proxy  '$remote_addr [$time_local] '
                           '$protocol $status $bytes_sent $bytes_received '
                           '$session_time "$upstream_addr" '
                           '"$upstream_bytes_sent" "$upstream_bytes_received" "$upstream_connect_time"';

        access_log /var/log/nginx/tcp-access.log  proxy;
        open_log_file_cache off;

        upstream cocossh {
            server 192.168.100.40:2222 weight=1;
            server 192.168.100.40:2223 weight=1;  # 多节点
            # 这里是 coco ssh 的后端ip
            hash $remote_addr;
        }
        server {
            listen 2222;
            proxy_pass cocossh;
            proxy_connect_timeout 10s;
            proxy_timeout 24h;   #代理超时
        }
    }

    http {
        include       /etc/nginx/mime.types;
        default_type  application/octet-stream;

        log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                          '$status $body_bytes_sent "$http_referer" '
                          '"$http_user_agent" "$http_x_forwarded_for"';

        access_log  /var/log/nginx/access.log  main;

        sendfile        on;
        # tcp_nopush     on;

        keepalive_timeout  65;

        # 关闭版本显示
        server_tokens off;

        include /etc/nginx/conf.d/*.conf;
    }

.. code-block:: nginx

    # 备份默认的配置文件
    $ mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.bak

    $ vi /etc/nginx/conf.d/jumpserver.conf

    upstream jumpserver {
        server 192.168.100.30:80;
        # 这里是 jumpserver 的后端ip
    }

    upstream cocows {
        server 192.168.100.40:5000 weight=1;
        server 192.168.100.40:5001 weight=1;  # 多节点
        # 这里是 coco ws 的后端ip
        ip_hash;
    }

    upstream guacamole {
        server 192.168.100.50:8081 weight=1;
        server 192.168.100.50:8082 weight=1;  # 多节点
        # 这里是 guacamole 的后端ip
        ip_hash;
    }

    server {
        listen 80;
        server_name www.jumpserver.org;  # 自行修改成你的域名
        return 301 https://$server_name$request_uri;
    }

    server {
        # 推荐使用 https 访问, 如果不使用 https 请自行注释下面的选项
        listen 443;
        server_name www.jumpserver.org;  # 自行修改成你的域名
        ssl on;
        ssl_certificate   /etc/nginx/sslkey/1_jumpserver.org_bundle.crt;  # 自行设置证书
        ssl_certificate_key  /etc/nginx/sslkey/2_jumpserver.org.key;  # 自行设置证书
        ssl_session_timeout 5m;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE:ECDH:AES:HIGH:!NULL:!aNULL:!MD5:!ADH:!RC4;
        ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
        ssl_prefer_server_ciphers on;

        client_max_body_size 100m;  # 录像上传大小限制

        location / {
            proxy_pass http://jumpserver;  # jumpserver
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;  # luna 路径, 如果修改安装目录, 此处需要修改
        }

        location /socket.io/ {
            proxy_pass       http://cocows/socket.io/;  # coco
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /coco/ {
            proxy_pass       http://cocows/coco/;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }

        location /guacamole/ {
            proxy_pass       http://guacamole/;  #  guacamole
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            access_log off;
        }
    }

.. code-block:: shell

    # nginx 测试并启动, 如果报错请按报错提示自行解决
    $ nginx -t
    $ systemctl start nginx

    # 访问 http://192.168.100.100
    # 默认账号: admin 密码: admin  到会话管理-终端管理 接受 Coco Guacamole 等应用的注册
    # 测试连接
    $ ssh -p2222 admin@192.168.100.100
    $ sftp -P2222 admin@192.168.100.100
    密码: admin

    # 如果是用在 Windows 下, Xshell Terminal 登录语法如下
    $ ssh admin@192.168.100.100 2222
    $ sftp admin@192.168.100.100 2222
    密码: admin
    如果能登陆代表部署成功

    # sftp默认上传的位置在资产的 /tmp 目录下
    # windows拖拽上传的位置在资产的 Guacamole RDP上的 G 目录下

后续的使用请参考 `快速入门 <admin_create_asset.html>`_
如遇到问题可参考 `FAQ <faq.html>`_
