from django.db.models import Q
from django.db.models import QuerySet
from assets.models import Asset, SystemUser
from users.models import User
from .models import AssetACLPolicy, PolicyTypeChoices, PolicyActionChoices


def get_acl_policies_by_user_asset_sys(user: User, asset: Asset, sys_user: SystemUser) -> QuerySet:
    jms_user = user.username
    asset_ip = asset.ip
    protocol_port = asset.protocols_as_dict.get(sys_user.protocol, 22)
    system_username = sys_user.username

    policies = AssetACLPolicy.objects.filter(
        is_active=True,
        policy_type=PolicyTypeChoices.asset.value,
        action=PolicyActionChoices.confirm.value,
        port=protocol_port,
    ).filter(
        Q(user=jms_user) | Q(user='*')
    ).filter(
        ip_start__lte=asset_ip,
        ip_end__gte=asset_ip,
    ).filter(
        Q(system_user=system_username) | Q(system_user='*'),
    )
    return policies
