from django.utils.translation import gettext_lazy as _
from rest_framework import status

from common.exceptions import JMSException


class MFANotEnabled(JMSException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'mfa_not_enabled'
    default_detail = _('MFA not enabled')


class PhoneNotSet(JMSException):
    default_code = 'phone_not_set'
    default_detail = _('Phone not set')


class UnableToDeleteAllUsers(JMSException):
    default_code = 'unable_to_delete_all_users'
    default_detail = _('Unable to delete all users')
