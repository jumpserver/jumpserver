from random import choice, sample
import forgery_py

from .base import FakeDataGenerator

from users.models import *
from assets.models import *
from perms.models import *


class AssetPermissionGenerator(FakeDataGenerator):
    resource = 'asset_permission'
    users_id: list
    user_groups_id: list
    assets_id: list
    nodes_id: list
    system_users_id: list

    def pre_generate(self):
        self.nodes_id = list(Node.objects.all().values_list('id', flat=True))
        self.assets_id = list(Asset.objects.all().values_list('id', flat=True))
        self.system_users_id = list(SystemUser.objects.all().values_list('id', flat=True))
        self.users_id = list(User.objects.all().values_list('id', flat=True))
        self.user_groups_id = list(UserGroup.objects.all().values_list('id', flat=True))

    def set_users(self, perms):
        through = AssetPermission.users.through
        choices = self.users_id
        relation_name = 'user_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_user_groups(self, perms):
        through = AssetPermission.user_groups.through
        choices = self.user_groups_id
        relation_name = 'usergroup_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_assets(self, perms):
        through = AssetPermission.assets.through
        choices = self.assets_id
        relation_name = 'asset_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_nodes(self, perms):
        through = AssetPermission.nodes.through
        choices = self.nodes_id
        relation_name = 'node_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_system_users(self, perms):
        through = AssetPermission.system_users.through
        choices = self.system_users_id
        relation_name = 'systemuser_id'
        self.set_relations(perms, through, relation_name, choices)

    def set_relations(self, perms, through, relation_name, choices, choice_count=None):
        relations = []

        for perm in perms:
            if choice_count is None:
                choice_count = choice(range(8))
            resources_id = sample(choices, choice_count)
            for rid in resources_id:
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
        self.set_system_users(created)
