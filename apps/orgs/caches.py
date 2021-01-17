from .cache import OrgRelatedCache, IntegerField
from users.models import UserGroup, User
from assets.models import Node, AdminUser, SystemUser, Domain, Gateway
from applications.models import Application
from perms.models import AssetPermission, ApplicationPermission
from .models import OrganizationMember


class OrgResourceStatisticsCache(OrgRelatedCache):
    users_amount = IntegerField()
    groups_amount = IntegerField(queryset=UserGroup.objects)

    assets_amount = IntegerField()
    nodes_amount = IntegerField(queryset=Node.objects)
    admin_users_amount = IntegerField(queryset=AdminUser.objects)
    system_users_amount = IntegerField(queryset=SystemUser.objects)
    domains_amount = IntegerField(queryset=Domain.objects)
    gateways_amount = IntegerField(queryset=Gateway.objects)

    applications_amount = IntegerField(queryset=Application.objects)

    asset_perms_amount = IntegerField(queryset=AssetPermission.objects)
    app_perms_amount = IntegerField(queryset=ApplicationPermission.objects)

    def __init__(self, org):
        super().__init__()
        self.org = org

    def get_key_suffix(self):
        return f'<org:{self.org.id}>'

    def get_current_org(self):
        return self.org

    def compute_users_amount(self):
        if self.org.is_real():
            users_amount = OrganizationMember.objects.values(
                'user_id'
            ).filter(org_id=self.org.id).distinct().count()
        else:
            users_amount = User.objects.all().distinct().count()
        return users_amount

    def compute_assets_amount(self):
        node = Node.org_root()
        return node.assets_amount
