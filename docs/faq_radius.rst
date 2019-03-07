Radius 使用说明
------------------------------

支持使用 Radius 的用户作为 jumpserver 登录用户

1. 修改 Jumpserver 配置文件启用 Radius 认证

.. code-block:: yaml

    $ vi /opt/jumpserver/config.yml

    # 在最后新增下面内容
    AUTH_RADIUS: True
    RADIUS_SERVER: 127.0.0.1
    RADIUS_PORT: 1812
    RADIUS_SECRET: radius_secret

    # 修改完成后保存, 重启 jumpserver 即可

2. 设置参数说明

.. code-block:: yaml

    # RADIUS_SERVER: 127.0.0.1 是 Radius 服务器的IP地址
    # RADIUS_PORT: 1812 是 Radius 服务器的端口
    # RADIUS_SECRET: radius_secret 是 Radius 服务器的预共享秘钥
    # freeradius 的 SECRET 在 clients.conf 里面
    # 思科的 SECRET 可以从 web 页面的 RADIUS Authentication Settings 里面的 Shared Secret 获取
    # 华为的 SECRET 可以从 web 页面的 Authentication Options 里面的 Shared Secret 获取
    # 其他厂商的请自行咨询相关厂商工作人员

    # 实际案例
    AUTH_RADIUS: True
    RADIUS_SERVER: 47.98.186.18
    RADIUS_PORT: 1812
    RADIUS_SECRET: testing123
