# -*- coding: utf-8 -*-
#
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri

from rest_framework.serializers import BooleanField


class HttpResponseTemporaryRedirect(HttpResponse):
    status_code = 307

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)


def get_remote_addr(request):
    return request.META.get("HTTP_X_FORWARDED_HOST") or request.META.get("REMOTE_ADDR")


def is_true(value):
    return value in BooleanField.TRUE_VALUES
