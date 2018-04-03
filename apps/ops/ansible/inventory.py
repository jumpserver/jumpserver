# ~*~ coding: utf-8 ~*~
from ansible.inventory.host import Host
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader


__all__ = [
    'BaseHost', 'BaseInventory'
]


class BaseHost(Host):
    def __init__(self, host_data):
        """
        初始化
        :param host_data:  {
            "hostname": "",
            "ip": "",
            "port": "",
            # behind is not must be required
            "username": "",
            "password": "",
            "private_key": "",
            "become": {
                "method": "",
                "user": "",
                "pass": "",
            }
            "groups": [],
            "vars": {},
        }
        """
        self.host_data = host_data
        hostname = host_data.get('hostname') or host_data.get('ip')
        port = host_data.get('port') or 22
        super().__init__(hostname, port)
        self.__set_required_variables()
        self.__set_extra_variables()

    def __set_required_variables(self):
        host_data = self.host_data
        self.set_variable('ansible_host', host_data['ip'])
        self.set_variable('ansible_port', host_data['port'])

        if host_data.get('username'):
            self.set_variable('ansible_user', host_data['username'])

        # 添加密码和秘钥
        if host_data.get('password'):
            self.set_variable('ansible_ssh_pass', host_data['password'])
        if host_data.get('private_key'):
            self.set_variable('ansible_ssh_private_key_file', host_data['private_key'])

        # 添加become支持
        become = host_data.get("become", False)
        if become:
            self.set_variable("ansible_become", True)
            self.set_variable("ansible_become_method", become.get('method', 'sudo'))
            self.set_variable("ansible_become_user", become.get('user', 'root'))
            self.set_variable("ansible_become_pass", become.get('pass', ''))
        else:
            self.set_variable("ansible_become", False)

    def __set_extra_variables(self):
        for k, v in self.host_data.get('vars', {}).items():
            self.set_variable(k, v)

    def __repr__(self):
        return self.name


class BaseInventory(InventoryManager):
    """
    提供生成Ansible inventory对象的方法
    """
    loader_class = DataLoader
    variable_manager_class = VariableManager
    host_manager_class = BaseHost

    def __init__(self, host_list=None, group_list=None):
        """
        用于生成动态构建Ansible Inventory. super().__init__ 会自动调用
        host_list: [{
            "hostname": "",
            "ip": "",
            "port": "",
            "username": "",
            "password": "",
            "private_key": "",
            "become": {
                "method": "",
                "user": "",
                "pass": "",
            },
            "groups": [],
            "vars": {},
          },
        ]
        group_list: [
          {"name: "", children: [""]},
        ]
        :param host_list:
        :param group_list
        """
        self.host_list = host_list or []
        self.group_list = group_list or []
        assert isinstance(host_list, list)
        self.loader = self.loader_class()
        self.variable_manager = self.variable_manager_class()
        super().__init__(self.loader)

    def get_groups(self):
        return self._inventory.groups

    def get_group(self, name):
        return self._inventory.groups.get(name, None)

    def get_or_create_group(self, name):
        group = self.get_group(name)
        if not group:
            self.add_group(name)
            return self.get_or_create_group(name)
        else:
            return group

    def parse_groups(self):
        for g in self.group_list:
            parent = self.get_or_create_group(g.get("name"))
            children = [self.get_or_create_group(n) for n in g.get('children', [])]
            for child in children:
                parent.add_child_group(child)

    def parse_hosts(self):
        group_all = self.get_or_create_group('all')
        ungrouped = self.get_or_create_group('ungrouped')
        for host_data in self.host_list:
            host = self.host_manager_class(host_data=host_data)
            self.hosts[host_data['hostname']] = host
            groups_data = host_data.get('groups')
            if groups_data:
                for group_name in groups_data:
                    group = self.get_or_create_group(group_name)
                    group.add_host(host)
            else:
                ungrouped.add_host(host)
            group_all.add_host(host)

    def parse_sources(self, cache=False):
        self.parse_groups()
        self.parse_hosts()

    def get_matched_hosts(self, pattern):
        return self.get_hosts(pattern)


