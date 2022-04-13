from django.db.models import Q
from perms.models import ApplicationPermission
from applications.models import Application
from applications.const import AppType
from jumpserver.utils import has_valid_xpack_license


def get_user_all_applicationpermission_ids(user):
    application_perm_ids = ApplicationPermission.objects.valid().filter(
        Q(users=user) | Q(user_groups__users=user)
    ).distinct().values_list('id', flat=True)
    return application_perm_ids


def get_user_granted_all_applications(user):
    application_perm_ids = get_user_all_applicationpermission_ids(user)
    q = Q(granted_by_permissions__id__in=application_perm_ids)
    if not has_valid_xpack_license():
        community_types = AppType.type_xpack_community_mapper()['community']
        q &= Q(type__in=community_types)
    applications = Application.objects.filter(q).distinct()
    return applications
