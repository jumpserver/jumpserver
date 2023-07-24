from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException


class BulkCreateNotSupport(JMSException):
    default_code = 'bulk_create_not_support'
    default_detail = _('Bulk create not support')


class StorageInvalid(JMSException):
    default_code = 'storage_invalid'
    default_detail = _('Storage is invalid')
