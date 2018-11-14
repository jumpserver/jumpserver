Firewalld 使用说明
------------------------------

1. 打开 firewalld

.. code-block:: shell

    $ systemctl start firewalld

2. 端口允许被某固定 IP 访问

.. code-block:: shell

    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="允许访问的IP" port protocol="tcp" port="端口" accept"
    $ firewall-cmd --reload  # 重载规则, 才能生效
    $ firewall-cmd --list-all  # 查看使用中的规则


    # 举例
    # 允许 192.168.100.166 访问 6379 端口
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="192.168.100.166" port protocol="tcp" port="6379" accept"

    # 允许 172.16.10.166 访问 3306 端口
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="172.16.10.166" port protocol="tcp" port="3306" accept"

    # 允许 10.10.10.166 访问 8080 端口
    $ firewall-cmd --permanent --add-rich-rule="rule family="ipv4" source address="10.10.10.166" port protocol="tcp" port="8080" accept"

    $ firewall-cmd --reload  # 重载规则, 才能生效

    # 删除规则( add 改成 remove )
    $ firewall-cmd --permanent --remove-rich-rule="rule family="ipv4" source address="192.168.100.166" port protocol="tcp" port="6379" accept"
    $ firewall-cmd --permanent --remove-rich-rule="rule family="ipv4" source address="172.16.10.166" port protocol="tcp" port="3306" accept"
    $ firewall-cmd --permanent --remove-rich-rule="rule family="ipv4" source address="10.10.10.166" port protocol="tcp" port="8080" accept"

    $ firewall-cmd --reload  # 重载规则, 才能生效

3. 端口允许所有 IP 访问

.. code-block:: shell

    $ firewall-cmd --zone=public --add-port=端口/tcp --permanent
    $ firewall-cmd --reload  # 重载规则, 才能生效
    $ firewall-cmd --list-all  # 查看使用中的规则

    # 举例
    # 允许访问 2222 端口
    $ firewall-cmd --zone=public --add-port=2222/tcp --permanent

    # 允许访问 8080 端口
    $ firewall-cmd --zone=public --add-port=8080/tcp --permanent


    # 删除规则( add 改成 remove )
    $ firewall-cmd --zone=public --remove-port=2222/tcp --permanent
    $ firewall-cmd --zone=public --remove-port=8080/tcp --permanent

    $ firewall-cmd --reload  # 重载规则, 才能生效
