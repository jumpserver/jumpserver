from django.utils.translation import gettext_lazy as _
from rest_framework import status

from common.exceptions import JMSException


class NodeIsBeingUpdatedByOthers(JMSException):
    status_code = status.HTTP_409_CONFLICT


class NotSupportedTemporarilyError(JMSException):
    default_detail = _("This function is not supported temporarily")
