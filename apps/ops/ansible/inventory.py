# ~*~ coding: utf-8 ~*~
import json
import os
import re
from collections import defaultdict

from django.utils.translation import gettext as _

__all__ = ['JMSInventory']


class JMSInventory:
    def __init__(
            self, assets, account_policy='privileged_first',
            account_prefer='root,Administrator', host_callback=None,
            exclude_localhost=False, task_type=None, protocol=None
    ):
        """
        :param assets:
        :param account_prefer: account username name if not set use account_policy
        :param account_policy: privileged_only, privileged_first, skip
        """
        self.assets = self.clean_assets(assets)
        self.account_prefer = self.get_account_prefer(account_prefer)
        self.account_policy = account_policy
        self.host_callback = host_callback
        self.exclude_hosts = {}
        self.exclude_localhost = exclude_localhost
        self.task_type = task_type
        self.protocol = protocol

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
                0, "sshpass -p {}".format(gateway.password)
            )
        if gateway.private_key:
            proxy_command_list.append("-i {}".format(gateway.private_key_path))

        proxy_command = "-o ProxyCommand='{}'".format(
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
            var['ansible_password'] = account.escape_jinja2_syntax(account.secret)
        elif account.secret_type == 'ssh_key':
            var['ansible_ssh_private_key_file'] = account.private_key_path
        return var

    @staticmethod
    def make_custom_become_ansible_vars(account, su_from_auth):
        su_method = su_from_auth['ansible_become_method']
        var = {
            'custom_become': True,
            'custom_become_method': su_method,
            'custom_become_user': account.su_from.username,
            'custom_become_password': account.escape_jinja2_syntax(account.su_from.secret),
            'custom_become_private_key_path': account.su_from.private_key_path
        }
        return var

    def make_account_vars(self, host, asset, account, automation, protocol, platform, gateway):
        from accounts.const import AutomationTypes
        if not account:
            host['error'] = _("No account available")
            return host

        port = protocol.port if protocol else 22
        host['ansible_host'] = asset.address
        host['ansible_port'] = port

        su_from = account.su_from
        if platform.su_enabled and su_from:
            su_from_auth = account.get_ansible_become_auth()
            host.update(su_from_auth)
            host.update(self.make_custom_become_ansible_vars(account, su_from_auth))
        elif platform.su_enabled and not su_from and \
                self.task_type in (AutomationTypes.change_secret, AutomationTypes.push_account):
            host.update(self.make_account_ansible_vars(account))
            host['ansible_become'] = True
            host['ansible_become_user'] = 'root'
            host['ansible_become_password'] = account.escape_jinja2_syntax(account.secret)
        else:
            host.update(self.make_account_ansible_vars(account))

        if gateway:
            ansible_connection = host.get('ansible_connection', 'ssh')
            if ansible_connection in ('local', 'winrm', 'rdp'):
                host['gateway'] = {
                    'address': gateway.address, 'port': gateway.port,
                    'username': gateway.username, 'secret': gateway.password,
                    'private_key_path': gateway.private_key_path
                }
                host['jms_asset']['port'] = port
            else:
                ansible_ssh_common_args = self.make_proxy_command(gateway)
                host['jms_asset'].update(ansible_ssh_common_args)
                host.update(ansible_ssh_common_args)

    def get_primary_protocol(self, ansible_config, protocols):
        invalid_protocol = type('protocol', (), {'name': 'null', 'port': 0})
        ansible_connection = ansible_config.get('ansible_connection')
        # 数值越小，优先级越高，若用户在 ansible_config 中配置了，则提高用户配置方式的优先级
        protocol_priority = {'ssh': 10, 'winrm': 9, ansible_connection: 1}
        if self.protocol:
            protocol_priority.update({self.protocol: 0})
        protocol_sorted = sorted(protocols, key=lambda x: protocol_priority.get(x.name, 999))
        protocol = protocol_sorted[0] if protocol_sorted else invalid_protocol
        return protocol

    @staticmethod
    def fill_ansible_config(ansible_config, protocol):
        if protocol.name in ('ssh', 'winrm', 'rdp'):
            ansible_config['ansible_connection'] = protocol.name
        if protocol.name == 'winrm':
            if protocol.setting.get('use_ssl', False):
                ansible_config['ansible_winrm_scheme'] = 'https'
                ansible_config['ansible_winrm_transport'] = 'ssl'
                ansible_config['ansible_winrm_server_cert_validation'] = 'ignore'
            else:
                ansible_config['ansible_winrm_scheme'] = 'http'
                ansible_config['ansible_winrm_transport'] = 'ntlm'
        return ansible_config

    def asset_to_host(self, asset, account, automation, protocols, platform):
        try:
            ansible_config = dict(automation.ansible_config)
        except (AttributeError, TypeError):
            ansible_config = {}

        protocol = self.get_primary_protocol(ansible_config, protocols)

        tp, category = asset.type, asset.category
        name = re.sub(r'[ \[\]/]', '_', asset.name)
        secret_info = {k: v for k, v in asset.secret_info.items() if v}
        host = {
            'name': name,
            'jms_asset': {
                'id': str(asset.id), 'name': asset.name, 'address': asset.address,
                'type': tp, 'category': category,
                'protocol': protocol.name, 'port': protocol.port,
                'spec_info': asset.spec_info, 'secret_info': secret_info,
                'protocols': [{'name': p.name, 'port': p.port} for p in protocols],
            },
            'jms_account': {
                'id': str(account.id), 'username': account.username,
                'secret': account.escape_jinja2_syntax(account.secret),
                'secret_type': account.secret_type, 'private_key_path': account.private_key_path
            } if account else None
        }

        protocols = host['jms_asset']['protocols']
        host['jms_asset'].update({f"{p['name']}_port": p['port'] for p in protocols})
        if host['jms_account'] and tp == 'oracle':
            host['jms_account']['mode'] = 'sysdba' if account.privileged else None

        ansible_config = self.fill_ansible_config(ansible_config, protocol)
        host.update(ansible_config)

        gateway = None
        if not asset.is_gateway and asset.domain:
            gateway = asset.domain.select_gateway()

        self.make_account_vars(
            host, asset, account, automation, protocol, platform, gateway
        )
        return host

    def get_asset_sorted_accounts(self, asset):
        accounts = list(asset.accounts.filter(is_active=True))
        connectivity_score = {'ok': 2, '-': 1, 'err': 0}
        sort_key = lambda x: (x.privileged, connectivity_score.get(x.connectivity, 0), x.date_updated)
        accounts_sorted = sorted(accounts, key=sort_key, reverse=True)
        return accounts_sorted

    @staticmethod
    def get_account_prefer(account_prefer):
        account_usernames = []
        if isinstance(account_prefer, str) and account_prefer:
            account_usernames = list(map(lambda x: x.lower(), account_prefer.split(',')))
        return account_usernames

    def get_refer_account(self, accounts):
        account = None
        if accounts:
            account = list(filter(
                lambda a: a.username.lower() in self.account_prefer, accounts
            ))
            account = account[0] if account else None
        return account

    def select_account(self, asset):
        accounts = self.get_asset_sorted_accounts(asset)
        if not accounts:
            return None

        refer_account = self.get_refer_account(accounts)
        if refer_account:
            return refer_account

        account_selected = accounts[0]
        if self.account_policy == 'skip':
            return None
        elif self.account_policy == 'privileged_first':
            return account_selected
        elif self.account_policy == 'privileged_only' and account_selected.privileged:
            return account_selected
        else:
            return None

    @staticmethod
    def set_platform_protocol_setting_to_asset(asset, platform_protocols):
        asset_protocols = asset.protocols.all()
        for p in asset_protocols:
            setattr(p, 'setting', platform_protocols.get(p.name, {}))
        return asset_protocols

    def generate(self, path_dir):
        hosts = []
        platform_assets = self.group_by_platform(self.assets)
        for platform, assets in platform_assets.items():
            automation = platform.automation
            platform_protocols = {
                p['name']: p['setting'] for p in platform.protocols.values('name', 'setting')
            }
            for asset in assets:
                protocols = self.set_platform_protocol_setting_to_asset(asset, platform_protocols)
                account = self.select_account(asset)
                host = self.asset_to_host(asset, account, automation, protocols, platform)

                if not automation.ansible_enabled:
                    host['error'] = _('Ansible disabled')

                if self.host_callback is not None:
                    host = self.host_callback(
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
                self.exclude_hosts[host['name']] = host['error']
        hosts = list(filter(lambda x: not x.get('error'), hosts))
        data = {'all': {'hosts': {}}}
        for host in hosts:
            name = host.pop('name')
            data['all']['hosts'][name] = host
        if not self.exclude_localhost:
            data['all']['hosts'].update({
                'localhost': {
                    'ansible_host': '127.0.0.1',
                    'ansible_connection': 'local'
                }
            })
        return data

    def write_to_file(self, path):
        path_dir = os.path.dirname(path)
        if not os.path.exists(path_dir):
            os.makedirs(path_dir, 0o700, True)
        data = self.generate(path_dir)
        with open(path, 'w') as f:
            f.write(json.dumps(data, indent=4))
