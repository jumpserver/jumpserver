from django.db.models import Q

from common.utils import get_logger
from perms.models import ApplicationPermission

logger = get_logger(__file__)


def get_application_system_users_id(user, application):
    queryset = ApplicationPermission.objects.valid()\
        .filter(
            Q(users=user) | Q(user_groups__users=user),
            Q(applications=application)
        ).values_list('system_users', flat=True)
    return queryset


def has_application_system_permission(user, application, system_user):
    system_users_id = get_application_system_users_id(user, application)
    return system_user.id in system_users_id
