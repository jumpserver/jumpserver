# -*- coding: utf-8 -*-
#

from .ansible.inventory import BaseInventory
from assets.utils import get_assets_by_hostname_list, get_system_user_by_name

__all__ = [
    'JMSInventory'
]


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
        if run_as_admin:
            host_list = [asset._to_secret_json() for asset in assets]
        else:
            host_list = [asset.to_json() for asset in assets]
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
