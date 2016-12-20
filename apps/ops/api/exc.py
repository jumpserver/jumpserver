# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, print_function

from rest_framework.exceptions import APIException
from django.utils.translation import ugettext as _


class ServiceUnavailable(APIException):
    status_code = default_code = 503
    default_detail = _('Service temporarily unavailable, try again later.')


class ServiceNotImplemented(APIException):
    status_code = default_code = 501
    default_detail = _('This service maybe implemented in the future, but now not implemented!')

