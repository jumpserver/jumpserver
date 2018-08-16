# -*- coding: utf-8 -*-
#

from .ansible.inventory import BaseInventory
from assets.utils import get_assets_by_fullname_list, get_system_user_by_name

__all__ = [
    'JMSInventory'
]


class JMSInventory(BaseInventory):
    """
    JMS Inventory is the manager with jumpserver assets, so you can
    write you own manager, construct you inventory
    """
    def __init__(self, hostname_list, run_as_admin=False, run_as=None, become_info=None):
        """
        :param hostname_list: ["test1", ]
        :param run_as_admin: True 是否使用管理用户去执行, 每台服务器的管理用户可能不同
        :param run_as: 是否统一使用某个系统用户去执行
        :param become_info: 是否become成某个用户去执行
        """
        self.hostname_list = hostname_list
        self.using_admin = run_as_admin
        self.run_as = run_as
        self.become_info = become_info

        assets = self.get_jms_assets()
        host_list = []

        for asset in assets:
            info = self.convert_to_ansible(asset, run_as_admin=run_as_admin)
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
        assets = get_assets_by_fullname_list(self.hostname_list)
        return assets

    def convert_to_ansible(self, asset, run_as_admin=False):
        info = {
            'id': asset.id,
            'hostname': asset.hostname,
            'ip': asset.ip,
            'port': asset.port,
            'vars': dict(),
            'groups': [],
        }
        if asset.domain and asset.domain.has_gateway():
            info["vars"].update(self.make_proxy_command(asset))
        if run_as_admin:
            info.update(asset.get_auth_info())
        for node in asset.nodes.all():
            info["groups"].append(node.value)
        for label in asset.labels.all():
            info["vars"].update({
                label.name: label.value
            })
            info["groups"].append("{}:{}".format(label.name, label.value))
        if asset.domain:
            info["vars"].update({
                "domain": asset.domain.name,
            })
            info["groups"].append("domain_"+asset.domain.name)
        return info

    def get_run_user_info(self):
        system_user = get_system_user_by_name(self.run_as)
        if not system_user:
            return {}
        else:
            return system_user._to_secret_json()

    @staticmethod
    def make_proxy_command(asset):
        gateway = asset.domain.random_gateway()
        proxy_command_list = [
            "ssh", "-p", str(gateway.port),
            "-o", "StrictHostKeyChecking=no",
            "{}@{}".format(gateway.username, gateway.ip),
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
