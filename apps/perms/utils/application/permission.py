from django.db.models import Q

from common.utils import get_logger
from perms.models import ApplicationPermission

logger = get_logger(__file__)


def get_application_system_users_id(user, application):
    queryset = ApplicationPermission.objects\
        .filter(Q(users=user) | Q(user_groups__users=user), Q(applications=application))\
        .valid()\
        .values_list('system_users', flat=True)
    return queryset
