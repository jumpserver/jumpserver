Linux 资产连接说明
----------------------------

1. 检查终端是否在线

::

    # 确定已经在Jumpserver后台 会话管理-终端管理 里接受 coco 的注册

    # 如果不在线请检查 Linux 组件是否正常运行，箭头指示处 绿色表示正常，红色表示异常
    $ ps -ef | grep cocod | grep -v grep
    $ netstat -an | grep ":2222" | grep -v grep

    # 如果不在线可以尝试重启 coco
    $ source /opt/py3/bin/activate
    $ cd /opt/coco
    $ ./cocod stop  # 请用 ps 命令确定 coco 进程已经退出后再继续操作
    $ ./cocod start  # 后台运行使用 -d 参数./cocod start -d

    # 如果重启后 coco 任然不在线，请重新注册
    # 在Jumpserver后台 会话管理-终端管理 删掉 coco 的注册
    $ cd /opt/coco && ./cocod stop
    $ rm /opt/coco/keys/.access_key  # coco, 如果你是按文档安装的，key应该在这里
    $ ./cocod start -d  # 正常运行后到Jumpserver 会话管理-终端管理 里面接受coco注册

.. image:: _static/img/faq_linux_01.jpg

2. 访问 luna 界面不显示资产信息

::

    # 确定已经授权资产给当前登录用户
    # 确定 umpserver 的版本与 luna 的版本一致，如不一致请参考升级文档进行处理

    # Jumpserver 版本可在 jumpserver页面右下角 看到
    # Luna 版本可在 luna页面左下角 看到

    # 注：更新后请清理浏览器缓存后再访问

.. image:: _static/img/faq_linux_02.jpg

3. 访问 Linux 资产无任何提示

::

    # 请参考第一条检查终端是否在线

.. image:: _static/img/faq_linux_03.jpg

4. 登录资产提示 Authentication failed

::

    # 请检查推送
    # 在 资产管理-系统用户 下，点击相应的 系统用户名称 可以看到 系统用户详情，右边可以测试

.. image:: _static/img/faq_linux_04.jpg

5. 推送成功后无法登录资产，或者推送的系统用户 id 不正确 home 目录权限错误

::

    # 登录该资产，删除掉错误权限的用户，然后重新推送即可

6. coco 启动时报错 Failed register terminal unknow: xxx-xxx.xxx

::

    # 这是因为当前系统的 hostname 有 coco 不支持的字符，需要手动指定 coco 的 NAME
    $ cd /opt/coco/
    $ vim conf.py

    # 项目名称, 会用来向Jumpserver注册, 识别而已, 不能重复
    # NAME = "localhost"
    NAME = "localhost"

其他问题可参考 `FAQ <faq.html>`_
