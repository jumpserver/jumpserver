# ~*~ coding: utf-8 ~*~
from collections import defaultdict
import json

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
            "name": "",
            "ip": "",
            "port": "",
            # behind is not must be required
            "username": "",
            "password": "",
            "private_key_path": "",
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
        hostname = host_data.get('name') or host_data.get('ip')
        port = host_data.get('port') or 22
        super().__init__(hostname, port)
        self.__set_required_variables()
        self.__set_extra_variables()

    def __set_required_variables(self):
        host_data = self.host_data
        self.set_variable('ansible_host', host_data['address'])
        self.set_variable('ansible_port', host_data['port'])

        if host_data.get('username'):
            self.set_variable('ansible_user', host_data['username'])

        # 添加密码和密钥
        if host_data.get('password'):
            self.set_variable('ansible_ssh_pass', host_data['password'])
        if host_data.get('private_key_path'):
            self.set_variable('ansible_ssh_private_key_file', host_data['private_key_path'])

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
            "name": "",
            "address": "",
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
            self.hosts[host_data['name']] = host
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


class JMSInventory:
    def __init__(self, assets, account_username=None, account_policy='smart', host_var_callback=None):
        """
        :param assets:
        :param account_username: account username name if not set use account_policy
        :param account_policy:
        :param host_var_callback:
        """
        self.assets = self.clean_assets(assets)
        self.account_username = account_username
        self.account_policy = account_policy
        self.host_var_callback = host_var_callback

    @staticmethod
    def clean_assets(assets):
        from assets.models import Asset
        asset_ids = [asset.id for asset in assets]
        assets = Asset.objects.filter(id__in=asset_ids)\
            .prefetch_related('platform', 'domain', 'accounts')
        return assets

    @staticmethod
    def group_by_platform(assets):
        groups = defaultdict(list)
        for asset in assets:
            groups[asset.platform].append(asset)
        return groups

    @staticmethod
    def make_proxy_command(gateway):
        proxy_command_list = [
            "ssh", "-o", "Port={}".format(gateway.port),
            "-o", "StrictHostKeyChecking=no",
            "{}@{}".format(gateway.username, gateway.address),
            "-W", "%h:%p", "-q",
        ]

        if gateway.password:
            proxy_command_list.insert(
                0, "sshpass -p '{}'".format(gateway.password)
            )
        if gateway.private_key:
            proxy_command_list.append("-i {}".format(gateway.private_key_file))

        proxy_command = "'-o ProxyCommand={}'".format(
            " ".join(proxy_command_list)
        )
        return {"ansible_ssh_common_args": proxy_command}

    def asset_to_host(self, asset, account, automation, protocols):
        host = {'name': asset.name, 'vars': {
            'asset_id': str(asset.id), 'asset_name': asset.name,
            'asset_type': asset.type, 'asset_category': asset.category,
        }}
        ansible_connection = automation.ansible_config.get('ansible_connection', 'ssh')
        gateway = None
        if asset.domain:
            gateway = asset.domain.select_gateway()

        ssh_protocol_matched = list(filter(lambda x: x.name == 'ssh', protocols))
        ssh_protocol = ssh_protocol_matched[0] if ssh_protocol_matched else None
        if ansible_connection == 'local':
            if gateway:
                host['ansible_host'] = gateway.address
                host['ansible_port'] = gateway.port
                host['ansible_user'] = gateway.username
                host['ansible_password'] = gateway.password
                host['ansible_connection'] = 'smart'
            else:
                host['ansible_connection'] = 'local'
        else:
            host['ansible_host'] = asset.address
            host['ansible_port'] = ssh_protocol.port if ssh_protocol else 22
            if account:
                host['ansible_user'] = account.username

                if account.secret_type == 'password' and account.secret:
                    host['ansible_password'] = account.secret
                elif account.secret_type == 'private_key' and account.secret:
                    host['ssh_private_key'] = account.private_key_file

            if gateway:
                host['vars'].update(self.make_proxy_command(gateway))

        if self.host_var_callback:
            callback_var = self.host_var_callback(asset)
            if isinstance(callback_var, dict):
                host['vars'].update(callback_var)
        return host

    def select_account(self, asset):
        accounts = list(asset.accounts.all())
        if not accounts:
            return None

        account_selected = None
        account_username = self.account_username

        if isinstance(self.account_username, str):
            account_username = [self.account_username]
        if account_username:
            for username in account_username:
                account_matched = list(filter(lambda account: account.username == username, accounts))
                if account_matched:
                    account_selected = account_matched[0]
                    return account_selected

        if not account_selected:
            if self.account_policy in ['privileged_must', 'privileged_first']:
                account_selected = list(filter(lambda account: account.is_privileged, accounts))
                account_selected = account_selected[0] if account_selected else None

        if not account_selected and self.account_policy == 'privileged_first':
            account_selected = accounts[0]
        return account_selected

    def generate(self):
        hosts = []
        platform_assets = self.group_by_platform(self.assets)
        for platform, assets in platform_assets.items():
            automation = platform.automation
            protocols = platform.protocols.all()

            if not automation.ansible_enabled:
                continue

            for asset in self.assets:
                account = self.select_account(asset)
                host = self.asset_to_host(asset, account, automation, protocols)
                hosts.append(host)
        return hosts

    def write_to_file(self, path):
        hosts = self.generate()
        data = {'all': {'hosts': {}}}
        for host in hosts:
            name = host.pop('name')
            var = host.pop('vars', {})
            host.update(var)
            data['all']['hosts'][name] = host
        with open(path, 'w') as f:
            f.write(json.dumps(data, indent=4))
