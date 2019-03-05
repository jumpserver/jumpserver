分布式部署文档 - redis 部署
----------------------------------------------------

说明
~~~~~~~
-  # 开头的行表示注释
-  $ 开头的行表示需要执行的命令

环境
~~~~~~~

-  系统: CentOS 7
-  IP: 192.168.100.20

+----------+------------+-----------------+---------------+------------------------+
| Protocol | ServerName |        IP       |      Port     |         Used By        |
+==========+============+=================+===============+========================+
|    TCP   |    Redis   | 192.168.100.20  |      6379     |        Jumpserver      |
+----------+------------+-----------------+---------------+------------------------+

开始安装
~~~~~~~~~~~~

.. code-block:: shell

    # 升级系统
    $ yum upgrade -y

    # 安装 redis 服务
    $ yum install -y install epel-release
    $ yum install -y redis

    # 设置防火墙, 开放 6379 端口 给 jumpserver 访问
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.30" port protocol="tcp" port="6379" accept"
    $ firewall-cmd --reload

    # 设置 redis 自启
    $ systemctl enable redis

.. code-block:: vim

    # 修改 redis 配置文件
    $ vi /etc/redis.conf

    ...

    # bind 127.0.0.1  # 注释这行, 新增如下内容
    bind 0.0.0.0
    requirepass weakPassword  # redis 连接密码
    maxmemory-policy allkeys-lru  # 清理策略, 优先移除最近未使用的key

    ...

.. code-block:: shell

    # 启动 redis
    $ systemctl start redis

    # redis 的主从设置请参考其官方, 之后会补上
