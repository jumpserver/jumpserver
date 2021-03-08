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
    admin_user_ids: list
    node_ids: list

    def pre_generate(self):
        self.admin_user_ids = list(AdminUser.objects.all().values_list('id', flat=True))
        self.node_ids = list(Node.objects.all().values_list('id', flat=True))

    def set_assets_nodes(self, assets):
        for asset in assets:
            nodes_id_add_to = random.sample(self.node_ids, 3)
            asset.nodes.add(*nodes_id_add_to)

    def do_generate(self, batch, batch_size):
        assets = []

        for i in batch:
            ip = forgery_py.internet.ip_v4()
            hostname = forgery_py.email.address().replace('@', '.')
            hostname = f'{hostname}-{ip}'
            data = dict(
                ip=ip,
                hostname=hostname,
                admin_user_id=choice(self.admin_user_ids),
                created_by='Fake',
                org_id=self.org.id
            )
            assets.append(Asset(**data))
        creates = Asset.objects.bulk_create(assets, ignore_conflicts=True)
        self.set_assets_nodes(creates)

    def after_generate(self):
        pass
