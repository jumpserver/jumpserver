from random import choice, sample
import forgery_py

from .base import FakeDataGenerator

from users.models import *
from assets.models import *
from perms.models import *


class AssetPermissionGenerator(FakeDataGenerator):
    resource = 'asset_permission'
    user_ids: list
    user_group_ids: list
    asset_ids: list
    node_ids: list
    system_user_ids: list

    def pre_generate(self):
        self.node_ids = list(Node.objects.all().values_list('id', flat=True))
        self.asset_ids = list(Asset.objects.all().values_list('id', flat=True))
        self.user_ids = list(User.objects.all().values_list('id', flat=True))
        self.user_group_ids = list(UserGroup.objects.all().values_list('id', flat=True))

    def set_users(self, perms):
        through = AssetPermission.users.through
        choices = self.user_ids
        relation_name = 'user_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_user_groups(self, perms):
        through = AssetPermission.user_groups.through
        choices = self.user_group_ids
        relation_name = 'usergroup_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_assets(self, perms):
        through = AssetPermission.assets.through
        choices = self.asset_ids
        relation_name = 'asset_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_nodes(self, perms):
        through = AssetPermission.nodes.through
        choices = self.node_ids
        relation_name = 'node_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_relations(self, perms, through, relation_name, choices, choice_count=None):
        relations = []

        for perm in perms:
            if choice_count is None:
                choice_count = choice(range(8))
            resource_ids = sample(choices, choice_count)
            for rid in resource_ids:
                data = {'assetpermission_id': perm.id}
                data[relation_name] = rid
                relations.append(through(**data))
        through.objects.bulk_create(relations, ignore_conflicts=True)

    def do_generate(self, batch, batch_size):
        perms = []

        for i in batch:
            name = forgery_py.basic.text()
            name = f'AssetPermission: {name}'
            perm = AssetPermission(name=name, org_id=self.org.id)
            perms.append(perm)
        created = AssetPermission.objects.bulk_create(perms, ignore_conflicts=True)
        self.set_users(created)
        self.set_user_groups(created)
        self.set_assets(created)
        self.set_nodes(created)
