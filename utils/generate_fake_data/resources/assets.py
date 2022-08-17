from random import choice
import random
import forgery_py

from .base import FakeDataGenerator

from assets.models import *


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
