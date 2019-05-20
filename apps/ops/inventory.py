# -*- coding: utf-8 -*-
#

from .ansible.inventory import BaseInventory
from assets.utils import get_assets_by_id_list, get_system_user_by_id

from common.utils import get_logger

__all__ = [
    'JMSInventory', 'JMSCustomInventory',
]


logger = get_logger(__file__)


class JMSBaseInventory(BaseInventory):

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
        if asset.domain:
            info["vars"].update({
                "domain": asset.domain.name,
            })
            info["groups"].append("domain_"+asset.domain.name)
        return info

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


class JMSInventory(JMSBaseInventory):
    """
    JMS Inventory is the manager with jumpserver assets, so you can
    write you own manager, construct you inventory,
    user_info  is obtained from admin_user or asset_user
    """
    def __init__(self, assets, run_as_admin=False, run_as=None, become_info=None):
        """
        :param host_id_list: ["test1", ]
        :param run_as_admin: True 是否使用管理用户去执行, 每台服务器的管理用户可能不同
        :param run_as: 用户名(添加了统一的资产用户管理器之后AssetUserManager加上之后修改为username)
        :param become_info: 是否become成某个用户去执行
        """
        self.assets = assets
        self.using_admin = run_as_admin
        self.run_as = run_as
        self.become_info = become_info

        host_list = []

        for asset in assets:
            info = self.convert_to_ansible(asset, run_as_admin=run_as_admin)
            host_list.append(info)

        if run_as:
            for host in host_list:
                run_user_info = self.get_run_user_info(host)
                host.update(run_user_info)

        if become_info:
            for host in host_list:
                host.update(become_info)
        super().__init__(host_list=host_list)

    def get_run_user_info(self, host):
        from assets.backends.multi import AssetUserManager

        if not self.run_as:
            return {}

        try:
            asset = self.assets.get(id=host.get('id'))
            run_user = AssetUserManager.get(self.run_as, asset)
        except Exception as e:
            logger.error(e, exc_info=True)
            return {}
        else:
            return run_user._to_secret_json()


class JMSCustomInventory(JMSBaseInventory):
    """
    JMS Custom Inventory is the manager with jumpserver assets,
    user_info  is obtained from custom parameter
    """

    def __init__(self, assets, username, password=None, public_key=None, private_key=None):
        """
        """
        self.assets = assets
        self.username = username
        self.password = password
        self.public_key = public_key
        self.private_key = private_key

        host_list = []

        for asset in assets:
            info = self.convert_to_ansible(asset)
            host_list.append(info)

        for host in host_list:
            run_user_info = self.get_run_user_info()
            host.update(run_user_info)

        super().__init__(host_list=host_list)

    def get_run_user_info(self):
        return {
            'username': self.username,
            'password': self.password,
            'public_key': self.public_key,
            'private_key': self.private_key
        }
