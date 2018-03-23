# -*- coding: utf-8 -*-
#
import random

from .ansible.inventory import BaseInventory
from assets.utils import get_assets_by_hostname_list, get_system_user_by_name

__all__ = [
    'JMSInventory'
]


def make_proxy_command(asset):
    gateway = random.choice(asset.domain.gateway_set.filter(is_active=True))

    proxy_command = [
        "ssh", "-p", str(gateway.port),
        "{}@{}".format(gateway.username, gateway.ip),
        "-W", "%h:%p", "-q",
    ]

    if gateway.password:
        proxy_command.insert(0, "sshpass -p {}".format(gateway.password))
    if gateway.private_key:
        proxy_command.append("-i {}".format(gateway.private_key_file))

    return {"ansible_ssh_common_args": "'-o ProxyCommand={}'".format(" ".join(proxy_command))}


class JMSInventory(BaseInventory):
    """
    JMS Inventory is the manager with jumpserver assets, so you can
    write you own manager, construct you inventory
    """
    def __init__(self, hostname_list, run_as_admin=False, run_as=None, become_info=None):
        self.hostname_list = hostname_list
        self.using_admin = run_as_admin
        self.run_as = run_as
        self.become_info = become_info

        assets = self.get_jms_assets()
        host_list = []

        for asset in assets:
            vars = {}
            if run_as_admin:
                info = asset._to_secret_json()
            else:
                info = asset.to_json()

            info["vars"] = vars
            if asset.domain and asset.domain.gateway_set.count():
                vars.update(make_proxy_command(asset))
                info.update(vars)

            host_list.append(info)

        if run_as:
            run_user_info = self.get_run_user_info()
            for host in host_list:
                host.update(run_user_info)
        if become_info:
            for host in host_list:
                host.update(become_info)
        super().__init__(host_list=host_list)

    def get_jms_assets(self):
        assets = get_assets_by_hostname_list(self.hostname_list)
        return assets

    def get_run_user_info(self):
        system_user = get_system_user_by_name(self.run_as)
        if not system_user:
            return {}
        else:
            return system_user._to_secret_json()
