开机自启
------------------

正常部署设置自启
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    # 启动
    $ vi /opt/start_jms.sh

    #!/bin/bash
    set -e

    export LANG=zh_CN.UTF-8

    # 项目安装位置, 默认是/opt
    Project=/opt

    pid=`ps -ef | grep -v grep | egrep '(gunicorn|celery|beat|cocod)' | awk '{print $2}'`
    if [ "$pid" != "" ]; then
        echo -e "\033[31m 检测到 Jumpserver 进程未退出, 结束中 \033[0m"
        cd /opt && sh stop_jms.sh
        sleep 5s
        pid1=`ps -ef | grep -v grep | egrep '(gunicorn|celery|beat|cocod)' | awk '{print $2}'`
        if [ "$pid1" != "" ]; then
            echo -e "\033[31m 检测到 Jumpserver 进程任未退出, 强制结束中 \033[0m"
            kill -9 ${pid1}
        fi
    fi

    echo -e "\033[31m 正常启动 Jumpserver ... \033[0m"

    # jumpserver
    source $Project/py3/bin/activate
    cd $Project/jumpserver && ./jms start -d

    # guacamole
    export GUACAMOLE_HOME=/config/guacamole
    export JUMPSERVER_KEY_DIR=/config/guacamole/keys
    export JUMPSERVER_SERVER=http://127.0.0.1:8080
    export BOOTSTRAP_TOKEN=******  # 根据实际情况修改
    /etc/init.d/guacd start
    cd /config/tomcat8/bin && ./startup.sh

    # coco
    cd $Project/coco && ./cocod start -d

    exit 0

.. code-block:: shell

    # 停止
    $ vi /opt/stop_jms.sh

    #!/bin/bash
    set -e

    # 项目安装位置, 默认是/opt
    Project=/opt

    source $Project/py3/bin/activate
    cd $Project/coco && ./cocod stop
    /etc/init.d/guacd stop
    cd /config/tomcat8/bin && ./shutdown.sh
    cd $Project/jumpserver && ./jms stop

    exit 0

.. code-block:: shell

    # 写入 rc.local
    $ chmod +x /etc/rc.local
    $ echo "sh /opt/start_jms.sh" >> /etc/rc.local


Docker 组件部署设置自启
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    # 启动
    $ vi /opt/start_jms.sh

    #!/bin/bash
    set -e

    export LANG=zh_CN.UTF-8

    # 项目安装位置, 默认是/opt
    Project=/opt

    pid=`ps -ef | grep -v grep | egrep '(gunicorn|celery|beat)' | awk '{print $2}'`
    if [ "$pid" != "" ]; then
        echo -e "\033[31m 检测到 Jumpserver 进程未退出, 结束中 \033[0m"
        cd /opt && sh stop_jms.sh
        sleep 5s
        pid1=`ps -ef | grep -v grep | egrep '(gunicorn|celery|beat)' | awk '{print $2}'`
        if [ "$pid1" != "" ]; then
            echo -e "\033[31m 检测到 Jumpserver 进程任未退出, 强制结束中 \033[0m"
            kill -9 ${pid1}
        fi
    fi

    echo -e "\033[31m 正常启动 Jumpserver ... \033[0m"
    source $Project/py3/bin/activate
    cd $Project/jumpserver && ./jms start -d
    docker start jms_coco
    docker start jms_guacamole

    exit 0

.. code-block:: shell

    # 停止
    $ vi /opt/stop_jms.sh

    #!/bin/bash
    set -e

    # 项目安装位置, 默认是/opt
    Project=/opt

    docker stop jms_coco
    docker stop jms_guacamole
    source $Project/py3/bin/activate
    cd $Project/jumpserver && ./jms stop

    exit 0

.. code-block:: shell

    # 写入 rc.local
    $ chmod +x /etc/rc.local
    $ echo "sh /opt/start_jms.sh" >> /etc/rc.local


Systemd 管理启动 Jumpserver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: shell

    # 适合按照一步一步文档进行安装的用户, Centos 7

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

    # Guacamole
    $ chkconfig guacd on
    $ sed -i '143i CATALINA_PID="$CATALINA_BASE/tomcat.pid"' /config/tomcat8/bin/catalina.sh
    $ vi /usr/lib/systemd/system/guacamole.service
    [Unit]
    Description=guacamole
    After=network.target jms.service
    Wants=jms.service

    [Service]
    Type=forking
    PIDFile=/config/tomcat8/tomcat.pid
    # BOOTSTRAP_TOKEN 根据实际情况修改
    Environment="JUMPSERVER_SERVER=http://127.0.0.1:8080" "JUMPSERVER_KEY_DIR=/config/guacamole/keys" "GUACAMOLE_HOME=/config/guacamole" "BOOTSTRAP_TOKEN=******"
    ExecStart=/config/tomcat8/bin/startup.sh
    ExecReload=
    ExecStop=/config/tomcat8/bin/shutdown.sh

    [Install]
    WantedBy=multi-user.target

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
