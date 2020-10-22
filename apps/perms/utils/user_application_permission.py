from perms.models import ApplicationPermission
from applications.models import Application


def get_user_all_applicationpermission_ids(user):
    application_perm_ids = set()
    application_perm_ids.update(
        ApplicationPermission.objects.valid().filter(users=user).distinct().values_list('id', flat=True)
    )
    application_perm_ids.update(
        ApplicationPermission.objects.valid().filter(user_groups__users=user).distinct().values_list('id', flat=True)
    )
    return application_perm_ids


def get_user_granted_all_applications(user):
    application_perm_ids = get_user_all_applicationpermission_ids(user)
    applications = Application.objects.filter(
        granted_by_permissions__id__in=application_perm_ids
    ).distinct()
    return applications
