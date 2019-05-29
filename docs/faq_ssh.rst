SSH 协议资产连接说明
--------------------------------

SSH 协议资产连接错误排查思路

.. code-block:: vim

    (1). 检查管理用户的权限是否正确, 权限需要与root权限一致
    (2). 检查资产的防火墙策略, 可以在资产上面新建个用户, 尝试用此用户在jumpserver服务器上进行ssh连接
    (3). 检查资产的ssh策略, 确保可以被jumpserver应用访问

1. 检查终端是否在线

.. image:: _static/img/faq_linux_01.jpg

.. code-block:: shell

    # 如果不在线请检查 coco 的 BOOTSTRAP_TOKEN 是否与 jumpserver 一致, 如果不一致请修改后重启
    # 在 终端管理 删除不在线的组件
    $ cat /opt/jumpserver/config.yml | grep BOOTSTRAP_TOKEN
    $ cat /opt/coco/config.yml | grep BOOTSTRAP_TOKEN

    $ cd /opt/coco && ./cocod stop
    $ rm /opt/coco/data/keys/.access_key  # coco, 如果你是按文档安装的, key应该在这里, 如果不存在, 直接下一步
    $ ./cocod start -d

    # docker 部署请直接删除容器后重建, 记得一定要先在 终端管理 删除不在线的组件
    $ docker stop jms_coco
    $ docker rm jms_coco

    # http://<Jumpserver_url> 指向 jumpserver 的服务url, 如 http://192.168.244.144:8080
    # BOOTSTRAP_TOKEN 为 Jumpserver/config.yml 里面的 BOOTSTRAP_TOKEN
    $ docker run --name jms_coco -d -p 2222:2222 -p 5000:5000 -e CORE_HOST=http://<Jumpserver_url> -e BOOTSTRAP_TOKEN=xxxxxx jumpserver/jms_coco:1.5.0

    # 正常运行后到Jumpserver 会话管理-终端管理 里面查看 coco 的状态是否为绿色

2. 访问 luna 界面不显示资产信息

.. code-block:: vim

    # 确定已经授权资产给当前登录用户
    # 确定 Jumpserver 的版本与 luna 的版本一致, 如不一致请参考升级文档进行处理

    # Jumpserver 版本可在 jumpserver页面右下角 看到
    # Luna 版本可在 luna页面左下角 看到

    # 注：更新后请清理浏览器缓存后再访问

.. image:: _static/img/faq_linux_02.jpg

3. 访问 Linux 资产无任何提示

.. code-block:: vim

    # 请参考第一条检查终端是否在线
    # 检查 coco 的 ws 端口(默认 5000)
    # 检查 nginx 配置的 socket.io 设置是否有误

    # 正常部署的 coco 组件请使用如下命令
    $ cd /opt/coco
    $ source /opt/py3/bin/activate
    $ ./cocod stop
    $ ps -ef | grep cocod | awk '{print $2}' | xargs kill -9
    $ ./cocod start

    # docker 容器部署的 coco 组件请检查防火墙是否无误, 重启容器即可
    $ docker restart jms_coco

.. image:: _static/img/faq_linux_03.jpg

4. 登录资产提示 Authentication failed

.. code-block:: vim

    # 请检查推送 或 系统用户 是否正确, 可以把系统用户设置成手动登录测试
    # 在 资产管理-系统用户 下, 点击相应的 系统用户名称 可以看到 系统用户详情, 右边可以测试

.. image:: _static/img/faq_linux_04.jpg

5. 测试可连接性 及 更新硬件信息

.. code-block:: vim

    # 注意不要拦截窗口

.. image:: _static/img/faq_linux_05.jpg
.. image:: _static/img/faq_linux_06.jpg

6. 管理用户 测试可连接性

.. code-block:: vim

    # 注意不要拦截窗口

.. image:: _static/img/faq_linux_07.jpg
.. image:: _static/img/faq_linux_08.jpg

7. 系统用户 推送 测试资产可连接性

.. code-block:: vim

    # 注意不要拦截窗口

.. image:: _static/img/faq_linux_09.jpg
.. image:: _static/img/faq_linux_10.jpg

8. ssh 使用key 登录资产提示 所选的用户密钥未在远程主机上注册

.. code-block:: vim

    # 这里是信息填写错误, ip端口应该填coco服务器的ip, 端口应该填coco服务的ssh端口(默认2222)

9. 清理celery产生的数据(无法正常推送及连接资产, 一直显示........等可以使用, 请确定字符集是zh_CN.UTF-8)

.. code-block:: shell

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ celery -A ops purge -f

    # 如果任然异常, 手动结束所有jumpserver进程, 然后kill掉未能正常结束的jumpserver相关进程, 在重新启动jumpserver即可

10. 连接测试常见错误

.. code-block:: vim

    # 提示 Authentication failure
    # 一般都是资产的管理用户不正确

    # 提示Failed to connect to the host via ssh: ssh_exchange_identification: read: Connection reset by peer\r\n
    # 一般是资产的 ssh 或者 防火墙 做了限制, 无法连接资产(资产信息填错也可能会报这个错误)
    # 检查防火墙设置以及 /etc/hosts.allow /etc/hosts.deny

    # 提示 "MODULE FAILURE", "module_stdout":"/bin/sh: 1: /usr/bin/python: not found\r\n", "module_stderr":"Shared connection to xx.xx.xx.xx closed.\r\n"
    # 一般是资产 python 未安装或者 python 异常

其他问题可参考 `FAQ <faq.html>`_
