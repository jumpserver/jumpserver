from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException


class BulkCreateNotSupport(JMSException):
    default_code = 'bulk_create_not_support'
    default_detail = _('Bulk create not support')
