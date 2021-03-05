from django.db.models import Q

from common.utils import get_logger
from perms.models import ApplicationPermission

logger = get_logger(__file__)


def get_application_system_user_ids(user, application):
    queryset = ApplicationPermission.objects.valid()\
        .filter(
            Q(users=user) | Q(user_groups__users=user),
            Q(applications=application)
        ).values_list('system_users', flat=True)
    return queryset


def has_application_system_permission(user, application, system_user):
    system_user_ids = get_application_system_user_ids(user, application)
    return system_user.id in system_user_ids
