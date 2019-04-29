开机自启
------------------

Systemd 管理自启
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 一步一步安装适用 (CentOS 7)

.. code-block:: vim

    # Jumpserver
    $ vi /usr/lib/systemd/system/jms.service
    [Unit]
    Description=jms
    After=network.target mariadb.service redis.service
    Wants=mariadb.service redis.service

    [Service]
    Type=forking
    Environment="PATH=/opt/py3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
    ExecStart=/opt/jumpserver/jms start all -d
    ExecReload=
    ExecStop=/opt/jumpserver/jms stop

    [Install]
    WantedBy=multi-user.target

.. code-block:: vim

    # Coco
    $ vi /usr/lib/systemd/system/coco.service
    [Unit]
    Description=coco
    After=network.target jms.service

    [Service]
    Type=forking
    PIDFile=/opt/coco/coco.pid
    Environment="PATH=/opt/py3/bin"
    ExecStart=/opt/coco/cocod start -d
    ExecReload=
    ExecStop=/opt/coco/cocod stop

    [Install]
    WantedBy=multi-user.target

.. code-block:: vim

    # Guacamole
    $ chkconfig guacd on
    $ vi /usr/lib/systemd/system/guacamole.service
    [Unit]
    Description=guacamole
    After=network.target jms.service
    Wants=jms.service

    [Service]
    Type=forking
    # PIDFile=/config/tomcat8/tomcat.pid
    # BOOTSTRAP_TOKEN 根据实际情况修改
    Environment="JUMPSERVER_SERVER=http://127.0.0.1:8080" "JUMPSERVER_KEY_DIR=/config/guacamole/keys" "GUACAMOLE_HOME=/config/guacamole" "BOOTSTRAP_TOKEN=******"
    ExecStart=/config/tomcat8/bin/startup.sh
    ExecReload=
    ExecStop=/config/tomcat8/bin/shutdown.sh

    [Install]
    WantedBy=multi-user.target

.. code-block:: shell

    # 开机自启设置
    $ systemctl enable jms
    $ systemctl enable coco
    $ systemctl enable guacamole

    # 启动
    $ systemctl start jms
    $ systemctl start coco
    $ systemctl start guacamole

    # 停止
    $ systemctl stop jms
    $ systemctl stop coco
    $ systemctl stop guacamole

Docker 组件部署自启 (Centos 7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 极速安装适用 (CentOS 7)
- 一体化部署适用 (CentOS 7)

.. code-block:: vim

    # Jumpserver
    $ vi /usr/lib/systemd/system/jms.service
    [Unit]
    Description=jms
    After=network.target mariadb.service redis.service docker.service
    Wants=mariadb.service redis.service docker.service

    [Service]
    Type=forking
    Environment="PATH=/opt/py3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
    ExecStart=/opt/jumpserver/jms start all -d
    ExecReload=
    ExecStop=/opt/jumpserver/jms stop

    [Install]
    WantedBy=multi-user.target

.. code-block:: vim

    # 启动
    $ vi /opt/start_jms.sh

    #!/bin/bash
    set -e

    export LANG=zh_CN.UTF-8

    systemctl start jms
    docker start jms_coco
    docker start jms_guacamole

    exit 0

.. code-block:: vim

    # 停止
    $ vi /opt/stop_jms.sh

    #!/bin/bash
    set -e

    export LANG=zh_CN.UTF-8

    docker stop jms_coco
    docker stop jms_guacamole
    systemctl stop jms

    exit 0

.. code-block:: shell

    # 写入 rc.local
    $ chmod +x /etc/rc.d/rc.local
    $ if [ "$(cat /etc/rc.local | grep start_jms.sh)" == "" ]; then echo "sh /opt/start_jms.sh" >> /etc/rc.local; fi

Docker 组件部署自启 (Ubuntu 18)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- 一体化部署适用 (Ubuntu 18)

.. code-block:: vim

    # Jumpserver
    $ vi /lib/systemd/system/jms.service
    [Unit]
    Description=jms
    After=network.target mysql.service redis-server.service docker.service
    Wants=mysql.service redis-server.service docker.service

    [Service]
    Type=forking
    Environment="PATH=/opt/py3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
    ExecStart=/opt/jumpserver/jms start all -d
    ExecReload=
    ExecStop=/opt/jumpserver/jms stop

    [Install]
    WantedBy=multi-user.target

.. code-block:: vim

    # 启动
    $ vi /opt/start_jms.sh

    #!/bin/bash
    set -e

    export LANG=zh_CN.utf8

    systemctl start jms
    docker start jms_coco
    docker start jms_guacamole

    exit 0

.. code-block:: vim

    # 停止
    $ vi /opt/stop_jms.sh

    #!/bin/bash
    set -e

    export LANG=zh_CN.utf8

    docker stop jms_coco
    docker stop jms_guacamole
    systemctl stop jms

    exit 0

.. code-block:: shell

    # 写入 rc.local
    $ chmod +x /etc/rc.d/rc.local
    $ if [ "$(cat /etc/rc.local | grep start_jms.sh)" == "" ]; then echo "sh /opt/start_jms.sh" >> /etc/rc.local; fi
