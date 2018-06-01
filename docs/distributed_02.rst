分布式部署文档 - nginx 代理部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  > 开头的行表示需要在 mysql 中执行
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
    $ yum -y install epel-release

    # 设置防火墙，开发 80 端口
    $ firewall-cmd --zone=public --add-port=80/tcp --permanent
    $ firewall-cmd --reload

    # 设置 http 访问权限
    $ setsebool -P httpd_can_network_connect 1

    # 安装 nginx
    $ yum -y install nginx
    $ systemctl enable nginx

    # 下载 luna
    $ cd /opt
    $ wget https://github.com/jumpserver/luna/releases/download/1.3.1/luna.tar.gz
    $ tar xvf luna.tar.gz
    $ chown -R root:root luna

    # 配置 Nginx（如果无法正常访问，请注释掉 nginx.conf 的 server 所有字段）
    $ vim /etc/nginx/conf.d/jumpserver.conf

    server {
        listen 80;

        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        location / {
            proxy_pass http://192.168.100.11;  # 192.168.100.11 是 jumpserver 服务器ip
        }

        location /luna/ {
            try_files $uri / /index.html;
            alias /opt/luna/;
        }

        location /socket.io/ {
            proxy_pass       http://192.168.100.12:5000/socket.io/;  # 192.168.100.12 是 coco 服务器ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /guacamole/ {
            proxy_pass       http://192.168.100.13:8081/;  # 192.168.100.13 是 docker 服务器ip
            proxy_buffering off;
            proxy_http_version 1.1;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $http_connection;
            access_log off;
        }
    }

::

    # nginx 测试并启动，如果报错请按报错提示自行解决
    $ nginx -t
    $ systemctl start nginx
