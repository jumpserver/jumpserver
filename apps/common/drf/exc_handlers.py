from django.core.exceptions import PermissionDenied, ObjectDoesNotExist as DJObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext
from rest_framework import exceptions
from rest_framework.views import set_rollback
from rest_framework.response import Response

from common.exceptions import JMSObjectDoesNotExist
from common.utils import get_logger

logger = get_logger(__name__)


def extract_object_name(exc, index=0):
    """
    `index` 是从 0 开始数的， 比如：
    `No User matches the given query.`
    提取 `User`，`index=1`
    """
    (msg, *_) = exc.args
    return gettext(msg.split(sep=' ', maxsplit=index + 1)[index])


def common_exception_handler(exc, context):
    logger.exception('')

    if isinstance(exc, Http404):
        exc = JMSObjectDoesNotExist(object_name=extract_object_name(exc, 1))
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, DJObjectDoesNotExist):
        exc = JMSObjectDoesNotExist(object_name=extract_object_name(exc, 0))

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    return None
