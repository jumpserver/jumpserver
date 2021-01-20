from random import choice
import random
import forgery_py

from .base import FakeDataGenerator

from assets.models import *


class AdminUsersGenerator(FakeDataGenerator):
    resource = 'admin_user'

    def do_generate(self, batch, batch_size):
        admin_users = []
        for i in batch:
            username = forgery_py.internet.user_name(True)
            password = forgery_py.basic.password()
            admin_users.append(AdminUser(
                name=username.title(),
                username=username,
                password=password,
                org_id=self.org.id,
                created_by='Fake',
            ))
        AdminUser.objects.bulk_create(admin_users, ignore_conflicts=True)


class SystemUsersGenerator(FakeDataGenerator):
    def do_generate(self, batch, batch_size):
        system_users = []
        protocols = list(dict(SystemUser.PROTOCOL_CHOICES).keys())
        for i in batch:
            username = forgery_py.internet.user_name(True)
            protocol = random.choice(protocols)
            name = username.title()
            name = f'{name}-{protocol}'
            system_users.append(SystemUser(
                name=name,
                username=username,
                password=forgery_py.basic.password(),
                protocol=protocol,
                org_id=self.org.id,
                created_by='Fake',
            ))
        SystemUser.objects.bulk_create(system_users, ignore_conflicts=True)


class NodesGenerator(FakeDataGenerator):
    resource = 'node'

    def do_generate(self, batch, batch_size):
        nodes_to_generate_children = list(Node.objects.all())
        for i in batch:
            parent = random.choice(nodes_to_generate_children)
            parent.create_child()


class AssetsGenerator(FakeDataGenerator):
    resource = 'asset'
    admin_users_id: list
    nodes_id: list

    def pre_generate(self):
        self.admin_users_id = list(AdminUser.objects.all().values_list('id', flat=True))
        self.nodes_id = list(Node.objects.all().values_list('id', flat=True))

    def set_assets_nodes(self, assets):
        assets_id = [asset.id for asset in assets]
        objs = []
        for asset_id in assets_id:
            nodes_id_add_to = random.sample(self.nodes_id, 3)
            objs_add = [Asset.nodes.through(asset_id=asset_id, node_id=nid) for nid in nodes_id_add_to]
            objs.extend(objs_add)
        Asset.nodes.through.objects.bulk_create(objs, ignore_conflicts=True)

    def do_generate(self, batch, batch_size):
        assets = []

        for i in batch:
            ip = forgery_py.internet.ip_v4()
            hostname = forgery_py.email.address().replace('@', '.')
            hostname = f'{hostname}-{ip}'
            data = dict(
                ip=ip,
                hostname=hostname,
                admin_user_id=choice(self.admin_users_id),
                created_by='Fake',
                org_id=self.org.id
            )
            assets.append(Asset(**data))
        creates = Asset.objects.bulk_create(assets, ignore_conflicts=True)
        self.set_assets_nodes(creates)

    def after_generate(self):
        pass
