from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import APIException


class HTTPNot200(APIException):
    default_code = 'http_not_200'
    default_detail = 'HTTP status is not 200'


class ErrCodeNot0(APIException):
    default_code = 'errcode_not_0'
    default_detail = 'Error code is not 0'


class ResponseDataKeyError(APIException):
    default_code = 'response_data_key_error'
    default_detail = 'Response data key error'


class NetError(APIException):
    default_code = 'net_error'
    default_detail = _('Network error, please contact system administrator')
