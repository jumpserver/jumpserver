FAQ
==========

1. Windows 无法连接

::

    (1). 如果白屏  可能是nginx设置的不对，也可能运行guacamole的docker容器有问题，总之请求到不了guacamole
    (2). 如果显示没有权限 可能是你在 终端管理里没有接受 guacamole的注册，请接受一下，如果还是不行，就删除刚才的注册，重启guacamole的docker重新注册
    (3). 如果显示未知问题 可能是你的资产填写的端口不对，或者授权的系统用户的协议不是rdp


2. 用户、系统用户、管理用户的关系

::

    用户：每个公司的同事创建一个用户账号，用来登录Jumpserver
    系统用户：使用来登录到服务器的用户，如 web, dba, root等
    管理用户：是服务器上已存在的特权用户，Ansible用来获取硬件信息, 如 root, 或者其它拥有 sudo NOPASSWD: ALL权限的用户
