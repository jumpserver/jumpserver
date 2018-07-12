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

开始安装
~~~~~~~~~~~~

::

    # 升级系统
    $ yum upgrade -y

    # 获取 epel-release 源
    $ yum -y install epel-release vim

    # 设置防火墙，开发 80 端口
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent
    $ firewall-cmd --reload

    # 设置 http 访问权限
    $ setsebool -P httpd_can_network_connect 1

::

    # 安装 nginx
    $ vim /etc/yum.repos.d/nginx.repo

    [nginx]
    name=nginx repo
    baseurl=http://nginx.org/packages/centos/7/$basearch/
    gpgcheck=0
    enabled=1

    # 非 Centos7 请参考 http://nginx.org/en/linux_packages.html#stable

::

    $ yum -y install nginx
    $ systemctl enable nginx

    # 下载 luna
    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.3.2/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

::

    # 配置 Nginx
    $ vim /etc/nginx/nginx.conf

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

        include /etc/nginx/conf.d/*.stream;
    }

    http {
        include       /etc/nginx/mime.types;
        default_type  application/octet-stream;

        log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                          '$status $body_bytes_sent "$http_referer" '
                          '"$http_user_agent" "$http_x_forwarded_for"';

        access_log  /var/log/nginx/access.log  main;

        sendfile        on;
        #tcp_nopush     on;

        keepalive_timeout  65;

        #关闭版本显示
        server_tokens off;

        #gzip 压缩传输
        gzip on;
        gzip_min_length 1k;
        gzip_buffers    4 16k;
        gzip_http_version 1.0;
        gzip_comp_level 2;
        gzip_types text/plain application/x-javascripttext/css application/xml;
        gzip_vary on;

        #配置代理参数
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 90;
        proxy_read_timeout 90;
        proxy_send_timeout 90;
        proxy_buffer_size 4k;

        #缓存配置
        proxy_temp_file_write_size 264k;
        proxy_temp_path /var/cache/nginx/nginx_temp;
        proxy_cache_path /var/cache/nginx/nginx_cache levels=1:2 keys_zone=cache_one:200m inactive=5d max_size=400m;
        proxy_ignore_headers X-Accel-Expires Expires Cache-Control Set-Cookie;

        include /etc/nginx/conf.d/*.conf;
    }

::

    $ vim /etc/nginx/conf.d/jumpserver.conf

    upstream jumpserver {
        server 192.168.100.11:80 max_fails=1 fail_timeout=120s;
        # server ip:port max_fails=1 fail_timeout=120s;
        # 这里是 jumpserver 的后端ip ，max_fails=1 fail_timeout=120s 是 HA 参数
    }

    upstream cocows {
        server 192.168.100.12:5000 max_fails=1 fail_timeout=120s;
        # server ip:port max_fails=1 fail_timeout=120s;
        # 这里是 coco ws 的后端ip ，max_fails=1 fail_timeout=120s 是 HA 参数
    }

    upstream guacamole {
        server 192.168.100.13:8081 max_fails=1 fail_timeout=120s;
        # server ip:port max_fails=1 fail_timeout=120s;
        # 这里是 guacamole 的后端ip ，max_fails=1 fail_timeout=120s 是 HA 参数
    }

    server {
        listen 80;

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        location / {
            proxy_pass http://jumpserver;  # jumpserver
        }

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;  # luna 路径，如果修改安装目录，此处需要修改
        }

        location /socket.io/ {
            proxy_pass       http://cocows/socket.io/;  # coco
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /guacamole/ {
            proxy_pass       http://guacamole/;  #  guacamole
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
            client_max_body_size 100m;  # Windows 文件上传大小限制
        }
    }

::

    $ vim /etc/nginx/conf.d/coco.stream

    stream {
        upstream cocossh {
            server 192.168.100.12:2222;
            # server ip:port max_fails=1 fail_timeout=120s;
            # 这里是 coco ssh 的后端ip ，max_fails=1 fail_timeout=120s 是 HA 参数
        }
        server {
            listen 2222;
            proxy_pass cocossh;
            proxy_connect_timeout 10s;
            proxy_timeout 24h;   #代理超时
        }
    }

::

    # nginx 测试并启动，如果报错请按报错提示自行解决
    $ nginx -t
    $ systemctl start nginx

    # 访问 http://192.168.100.100
    # 默认账号: admin 密码: admin  到会话管理-终端管理 接受 Coco Guacamole 等应用的注册
    # 测试连接
    $ ssh -p2222 admin@192.168.100.100
    $ sftp -P2222 admin@192.168.100.100
    密码: admin

    # 如果是用在 Windows 下，Xshell Terminal 登录语法如下
    $ ssh admin@192.168.100.100 2222
    $ sftp admin@192.168.100.100 2222
    密码: admin
    如果能登陆代表部署成功

    # sftp默认上传的位置在资产的 /tmp 目录下
    # windows拖拽上传的位置在资产的 Guacamole RDP上的 G 目录下

    后续的使用请参考 `快速入门 <admin_create_asset.html>`_
    如遇到问题可参考 `FAQ <faq.html>`_
