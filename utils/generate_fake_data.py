#!/usr/bin/env python
#
import os
import sys
import django
import argparse
from random import seed, choice
import random
from itertools import islice


if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from assets.models import *
from assets.utils import check_node_assets_amount
from orgs.models import Organization


class FakeDataGenerator:
    resource = 'Fake'

    def __init__(self, batch_size=100, org_id=None):
        self.batch_size = batch_size
        self.org = self.switch_org(org_id)
        seed()

    def switch_org(self, org_id):
        o = Organization.get_instance(org_id, default=True)
        if o:
            o.change_to()
        print('Current org is: {}'.format(o))
        return o

    def do_generate(self, batch, batch_size):
        raise NotImplementedError

    def pre_generate(self):
        pass

    def after_generate(self):
        pass

    def generate(self, count=100):
        self.pre_generate()
        counter = iter(range(count))
        created = 0
        while True:
            batch = list(islice(counter, self.batch_size))
            if not batch:
                break
            self.do_generate(batch, self.batch_size)
            from_size = created
            created += len(batch)
            print('Generate %s: %s-%s' % (self.resource, from_size, created))
        self.after_generate()


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
            ip = [str(i) for i in random.sample(range(255), 4)]
            data = dict(
                ip='.'.join(ip),
                hostname='.'.join(ip),
                admin_user_id=choice(self.admin_users_id),
                created_by='Fake',
                org_id=self.org.id
            )
            assets.append(Asset(**data))
        creates = Asset.objects.bulk_create(assets, ignore_conflicts=True)
        self.set_assets_nodes(creates)

    def after_generate(self):
        check_node_assets_amount()


resource_generator_mapper = {
    'asset': AssetsGenerator,
    'node': NodesGenerator
}


def main():
    parser = argparse.ArgumentParser(description='Generate fake data')
    parser.add_argument(
        'resource', type=str,
        choices=resource_generator_mapper.keys(),
        help="resource to generate"
    )
    parser.add_argument('-c', '--count', type=int, default=100)
    parser.add_argument('-b', '--batch_size', type=int, default=100)
    parser.add_argument('-o', '--org', type=str, default='')
    args = parser.parse_args()
    resource, count, batch_size, org_id = args.resource, args.count, args.batch_size, args.org
    generator_cls = resource_generator_mapper[resource]
    generator = generator_cls(org_id=org_id, batch_size=batch_size)
    generator.generate(count)


if __name__ == '__main__':
    main()
