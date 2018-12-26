Telnet 使用说明
------------------------------

资产的创建与系统用户的创建与ssh大同小异

1. telnet 连不上

.. code-block:: shell

    # 这是因为coco无法判断telnet的返回状态导致的,需要修改如下代码
    $ vi /opt/coco/coco/connection.py  # 第 174 行

.. code-block:: python

    class TelnetConnection:

        def __init__(self, asset, system_user, client):
            self.client = client
            self.asset = asset
            self.system_user = system_user
            self.sock = None
            self.sel = selectors.DefaultSelector()
            self.incorrect_pattern = re.compile(
                r'incorrect|failed|失败|错误', re.I
            )
            self.username_pattern = re.compile(
                r'login:\s*$|username:\s*$|用户名:\s*$|账\s*号:\s*$', re.I
            )
            self.password_pattern = re.compile(
                r'password:\s*$|passwd:\s*$|密\s*码:\s*$', re.I
            )
            self.success_pattern = re.compile(
                r'Last\s*login|success|成功', re.I
            )

.. code-block:: vim

    # 在 'incorrect|failed|失败|错误|在这里加入你设备登录失败的提示符|可以多个|可以正则匹配'
    # 在 'Last\s*login|success|成功|在这里加入你设备登录成功的提示符|可以多个|可以正则匹配'

    例：XX路由器  使用 telnet 命令登录成功提示符#   登录失败提示Error
    修改 'incorrect|failed|失败|错误|Error'
    修改 'Last\s*login|success|成功|#'

    其实就是通过 tenlet 命令登录成功和失败的返回字符串加上，让代码能正确判断登录成功和失败

    是 通过 tenlet 命令登录 成功和失败 的返回字符串
    是 通过 telnet 命令登录
    是 telnet 命令登录

    # 保存后需要重启coco组件

    # 你也可以把你的设备登录成功和登录失败的信息发到jumpserver的项目问题里面,我们会在下个版本更新代码以支持你的设备
