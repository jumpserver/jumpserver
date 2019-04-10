Telnet 使用说明
------------------------------

资产的创建与系统用户的创建选择telnet

1. telnet 连不上

.. code-block:: vim

    # 需要在 Web "系统设置"-"终端设置" 添加成功判断代码
    # 是 通过 "tenlet" 命令登录 telnet设备 "成功" 的返回字符串

    # 保存后需要重启coco组件

2. 举例

.. code-block:: shell

    $ telnet 172.16.0.1

    Login authentication

    login: admin
    password: *********
    Info: The max number or VTY users is 10, and the number
          of current VTY users on line is 1.
    <RA-L7-RD>

    # 把 <RA-L7-RD> 写入到 Web "系统设置"-"终端设置"-"Telnet 成功正则表达式" 里面, 多个不一样的字符串用 | 隔开, 如 <RA-L7-RD>|<CHXZ-Group-S7503-LB2>|success|成功
    # <RA-L7-RD> 正则可用 <.*>+? 表示
