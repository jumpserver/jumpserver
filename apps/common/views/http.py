# -*- coding: utf-8 -*-
#
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri


class HttpResponseTemporaryRedirect(HttpResponse):
    status_code = 307

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)

