from rest_framework import status
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException


class AdminIsModifyingPerm(JMSException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('The administrator is modifying permissions. Please wait')


class CanNotRemoveAssetPermNow(JMSException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('The authorization cannot be revoked for the time being')
