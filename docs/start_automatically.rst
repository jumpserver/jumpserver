开机自启
------------------

设置 Jumpserver 自启

::

    # 启动
    $ vim /opt/start_jms.sh

    #!/bin/bash
    set -e

    # 项目安装位置，默认是/opt
    Project=/opt

    pid=`ps -ef | grep -v grep | egrep '(gunicorn|celery|beat|cocod)' | awk '{print $2}'`
    if [ "$pid" != "" ]; then
        echo -e "\033[31m 检测到 Jumpserver 进程未退出，结束中 \033[0m"
        cd /opt && sh stop_jms.sh
        sleep 5s
        pid1=`ps -ef | grep -v grep | egrep '(gunicorn|celery|beat|cocod)' | awk '{print $2}'`
        if [ "$pid1" != "" ]; then
            echo -e "\033[31m 检测到 Jumpserver 进程任未退出，强制结束中 \033[0m"
            kill -9 ${pid1}
        fi
    fi

    echo -e "\033[31m 正常启动 Jumpserver ... \033[0m"
    source $Project/py3/bin/activate
    cd $Project/jumpserver && ./jms start -d
    /etc/init.d/guacd start
    cd /config/tomcat8/bin && ./startup.sh
    cd $Project/coco && ./cocod start -d

    exit 0

::

    # 停止
    $ vim /opt/stop_jms.sh

    #!/bin/bash
    set -e

    # 项目安装位置，默认是/opt
    Project=/opt

    source $Project/py3/bin/activate
    cd $Project/coco && ./cocod stop
    /etc/init.d/guacd stop
    cd /config/tomcat8/bin && ./shutdown.sh
    cd $Project/jumpserver && ./jms stop

    exit 0

::

    # 写入 rc.local
    $ chmod +x /etc/rc.local
    $ echo "sh /opt/start_jms.sh" >> /etc/rc.local
