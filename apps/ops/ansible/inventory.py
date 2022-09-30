# ~*~ coding: utf-8 ~*~
from collections import defaultdict
import json


__all__ = [
    'JMSInventory',
]


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
