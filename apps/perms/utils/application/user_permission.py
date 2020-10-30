from django.db.models import Q
from perms.models import ApplicationPermission
from applications.models import Application


def get_user_all_applicationpermissions_id(user):
    application_perm_ids = ApplicationPermission.objects.valid().filter(
        Q(users=user) | Q(user_groups__users=user)
    ).distinct().values_list('id', flat=True)
    return application_perm_ids


def get_user_granted_all_applications(user):
    application_perms_id = get_user_all_applicationpermissions_id(user)
    applications = Application.objects.filter(
        granted_by_permissions__id__in=application_perms_id
    ).distinct()
    return applications
