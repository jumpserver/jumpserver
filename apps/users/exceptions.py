from django.utils.translation import gettext_lazy as _
from rest_framework import status

from common.exceptions import JMSException


class MFANotEnabled(JMSException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'mfa_not_enabled'
    default_detail = _('MFA not enabled')
