# ~*~ coding: utf-8 ~*~
from ansible.inventory import Inventory, Host, Group
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader


class JMSHost(Host):
    def __init__(self, asset):
        self.asset = asset
        self.name = name = asset.get('hostname') or asset.get('ip')
        self.port = port = asset.get('port') or 22
        super(JMSHost, self).__init__(name, port)
        self.set_all_variable()

    def set_all_variable(self):
        asset = self.asset
        self.set_variable('ansible_host', asset['ip'])
        self.set_variable('ansible_port', asset['port'])
        self.set_variable('ansible_user', asset['username'])

        # 添加密码和秘钥
        if asset.get('password'):
            self.set_variable('ansible_ssh_pass', asset['password'])
        if asset.get('private_key'):
            self.set_variable('ansible_ssh_private_key_file', asset['private_key'])

        # 添加become支持
        become = asset.get("become", False)
        if become:
            self.set_variable("ansible_become", True)
            self.set_variable("ansible_become_method", become.get('method', 'sudo'))
            self.set_variable("ansible_become_user", become.get('user', 'root'))
            self.set_variable("ansible_become_pass", become.get('pass', ''))
        else:
            self.set_variable("ansible_become", False)


class JMSInventory(Inventory):
    """
    提供生成Ansible inventory对象的方法
    """

    def __init__(self, host_list=None):
        if host_list is None:
            host_list = []
        assert isinstance(host_list, list)
        self.host_list = host_list
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        super(JMSInventory, self).__init__(self.loader, self.variable_manager,
                                           host_list=host_list)

    def parse_inventory(self, host_list):
        """用于生成动态构建Ansible Inventory.
        self.host_list: [
            {"name": "asset_name",
             "ip": <ip>,
             "port": <port>,
             "user": <user>,
             "pass": <pass>,
             "key": <sshKey>,
             "groups": ['group1', 'group2'],
             "other_host_var": <other>},
             {...},
        ]

        :return: 返回一个Ansible的inventory对象
        """

        # TODO: 验证输入
        # 创建Ansible Group,如果没有则创建default组
        ungrouped = Group('ungrouped')
        all = Group('all')
        all.add_child_group(ungrouped)
        self.groups = dict(all=all, ungrouped=ungrouped)

        for asset in host_list:
            host = JMSHost(asset=asset)
            asset_groups = asset.get('groups')
            if asset_groups:
                for group_name in asset_groups:
                    if group_name not in self.groups:
                        group = Group(group_name)
                        self.groups[group_name] = group
                    else:
                        group = self.groups[group_name]
                    group.add_host(host)
            else:
                ungrouped.add_host(host)
            all.add_host(host)

