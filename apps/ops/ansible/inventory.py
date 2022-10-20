# ~*~ coding: utf-8 ~*~
import json
import os
from collections import defaultdict

from django.utils.translation import gettext as _

__all__ = ['JMSInventory']


class JMSInventory:
    def __init__(self, manager, assets=None, account_policy='smart', account_prefer='root,administrator'):
        """
        :param assets:
        :param account_prefer: account username name if not set use account_policy
        :param account_policy: smart, privileged_must, privileged_first
        """
        self.manager = manager
        self.assets = self.clean_assets(assets)
        self.account_prefer = account_prefer
        self.account_policy = account_policy

    @staticmethod
    def clean_assets(assets):
        from assets.models import Asset
        asset_ids = [asset.id for asset in assets]
        assets = Asset.objects.filter(id__in=asset_ids, is_active=True) \
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

    @staticmethod
    def make_account_ansible_vars(account):
        var = {
            'ansible_user': account.username,
        }
        if not account.secret:
            return var
        if account.secret_type == 'password':
            var['ansible_password'] = account.secret
        elif account.secret_type == 'ssh_key':
            var['ansible_ssh_private_key_file'] = account.private_key_file
        return var

    def make_ssh_account_vars(self, host, asset, account, automation, protocols, platform, gateway):
        if not account:
            host['error'] = _("No account available")
            return host

        ssh_protocol_matched = list(filter(lambda x: x.name == 'ssh', protocols))
        ssh_protocol = ssh_protocol_matched[0] if ssh_protocol_matched else None
        host['ansible_host'] = asset.address
        host['ansible_port'] = ssh_protocol.port if ssh_protocol else 22

        su_from = account.su_from
        if platform.su_enabled and su_from:
            host.update(self.make_account_ansible_vars(su_from))
            become_method = 'sudo' if platform.su_method != 'su' else 'su'
            host['ansible_become'] = True
            host['ansible_become_method'] = 'sudo'
            host['ansible_become_user'] = account.username
            if become_method == 'sudo':
                host['ansible_become_password'] = su_from.secret
            else:
                host['ansible_become_password'] = account.secret
        else:
            host.update(self.make_account_ansible_vars(account))

        if gateway:
            host.update(self.make_proxy_command(gateway))

    def asset_to_host(self, asset, account, automation, protocols, platform):
        host = {
            'name': '{}'.format(asset.name),
            'jms_asset': {
                'id': str(asset.id), 'name': asset.name, 'address': asset.address,
                'type': asset.type, 'category': asset.category,
                'protocol': asset.protocol, 'port': asset.port,
                'protocols': [{'name': p.name, 'port': p.port} for p in protocols],
            },
            'jms_account': {
                'id': str(account.id), 'username': account.username,
                'secret': account.secret, 'secret_type': account.secret_type
            } if account else None
        }
        ansible_config = dict(automation.ansible_config)
        ansible_connection = ansible_config.get('ansible_connection', 'ssh')
        host.update(ansible_config)
        gateway = None
        if asset.domain:
            gateway = asset.domain.select_gateway()

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
            self.make_ssh_account_vars(host, asset, account, automation, protocols, platform, gateway)
        return host

    def select_account(self, asset):
        accounts = list(asset.accounts.all())
        account_selected = None
        account_username = self.account_prefer

        if isinstance(self.account_prefer, str):
            account_username = self.account_prefer.split(',')

        if account_username:
            for username in account_username:
                account_matched = list(filter(lambda account: account.username == username, accounts))
                if account_matched:
                    account_selected = account_matched[0]
                    break

        if not account_selected:
            if self.account_policy in ['privileged_must', 'privileged_first']:
                account_matched = list(filter(lambda account: account.privileged, accounts))
                account_selected = account_matched[0] if account_matched else None

        if not account_selected and self.account_policy == 'privileged_first':
            account_selected = accounts[0] if accounts else None
        return account_selected

    def generate(self, path_dir):
        hosts = []
        platform_assets = self.group_by_platform(self.assets)
        for platform, assets in platform_assets.items():
            automation = platform.automation
            protocols = platform.protocols.all()

            for asset in assets:
                account = self.select_account(asset)
                host = self.asset_to_host(asset, account, automation, protocols, platform)

                if not automation.ansible_enabled:
                    host['error'] = _('Ansible disabled')

                if self.manager.host_callback is not None:
                    host = self.manager.host_callback(
                        host, asset=asset, account=account,
                        platform=platform, automation=automation,
                        path_dir=path_dir
                    )

                if isinstance(host, list):
                    hosts.extend(host)
                else:
                    hosts.append(host)

        exclude_hosts = list(filter(lambda x: x.get('error'), hosts))
        if exclude_hosts:
            print(_("Skip hosts below:"))
            for i, host in enumerate(exclude_hosts, start=1):
                print("{}: [{}] \t{}".format(i, host['name'], host['error']))

        hosts = list(filter(lambda x: not x.get('error'), hosts))
        data = {'all': {'hosts': {}}}
        for host in hosts:
            name = host.pop('name')
            data['all']['hosts'][name] = host
        return data

    def write_to_file(self, path):
        path_dir = os.path.dirname(path)
        data = self.generate(path_dir)
        if not os.path.exists(path_dir):
            os.makedirs(path_dir, 0o700, True)
        with open(path, 'w') as f:
            f.write(json.dumps(data, indent=4))
