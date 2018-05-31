Windows 资产连接说明
----------------------------

1. 检查终端是否在线

::

    # 如果不在线请检查 Windows 组件是否已经正常运行
    $ docker ps

    # 如果已经正常运行，但是终端没有 guacamole 的注册请求
    $ systemctl status firewalld  # 检查防火墙是否运行，如果防火墙运行请开放 guacamole 端口

    $ docker stop jms_guacamole  # 如果名称更改过或者不对，请使用docker ps 查询容器的 CONTAINER ID ，然后docker stop <CONTAINER ID>
    $ docker rm jms_guacamole  # 如果名称更改过或者不对，请使用docker ps -a 查询容器的 CONTAINER ID ，然后docker rm <CONTAINER ID>
    $ rm /opt/guacamole/key/*  # guacamole, 如果你是按文档安装的，key应该在这里
    $ systemctl stop docker
    $ systemctl start docker
    $ docker run --name jms_guacamole -d \
      -p 8081:8080 -v /opt/guacamole/key:/config/guacamole/key \
      -e JUMPSERVER_KEY_DIR=/config/guacamole/key \
      -e JUMPSERVER_SERVER=http://<填写jumpserver的url地址> \
      registry.jumpserver.org/public/guacamole:latest

    # 如果registry.jumpserver.org/public/guacamole:latest下载很慢，可以换成jumpserver/guacamole:latest

    # 正常运行后到Jumpserver 会话管理-终端管理 里面接受gua注册
    $ docker restart jms_guacamole  # 如果接受注册后显示不在线，重启gua就好了

.. image:: _static/img/faq_windows_01.jpg

2. 登录要连接的windows资产，检查用户和IP信息（Windows目前还不支持推送，所以必须使用资产上面已存在的用户进行登录）

::

    # 注：因为 windows 暂时不支持推送，所以必须使用资产上面已经存在的账户进行登录，如 administrator 账户
    $ net user  # 在 windows 资产上用此命令查询已有用户

.. image:: _static/img/faq_windows_02.jpg

3. 创建Windows资产管理用户（如果是域资产，格式是uesr@domain.com）

::

    # 不带域的用户直接输入用户名即可，如 administrator
    # 域用户的用户名格式为 user@domain.com，如 administrator@jumpserver.org

.. image:: _static/img/faq_windows_03.jpg

4. 创建Windows资产系统用户（如果是域资产，格式是uesr@domain.com，注意协议不要选错）

::

    # 注：因为 windows 暂时不支持推送，所以必须使用资产上面已经存在的账户进行登录，如 administrator 账户
    # 不带域的用户直接输入用户名即可，如 administrator
    # 域用户的用户名格式为 user@domain.com，如 administrator@jumpserver.org

.. image:: _static/img/faq_windows_04.jpg

5. 创建Windows资产（注意端口不要填错）

.. image:: _static/img/faq_windows_05.jpg

6. 创建授权规则

::

    # 先定位到 windows 的资产，然后授权，如果资产用户密码不一致，请不要直接在节点上授权

.. image:: _static/img/faq_windows_06.jpg

7. 使用web terminal登录（如果登录报错，检查防火墙的设置，可以参考FAQ）

.. image:: _static/img/faq_windows_07.jpg

8. 上传文件到 windows

::

    # 直接拖拽文件到 windows 窗口即可，文件上传后在 Guacamole RDP上的 G 目录查看

.. image:: _static/img/faq_windows_08.jpg

其他问题可参考 `FAQ <faq.html>`_
