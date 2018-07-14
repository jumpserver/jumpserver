# -*- coding: utf-8 -*-
#

from .utils import get_org_from_request, set_current_org
from .models import Organization


class OrgPreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_org(Organization.root())
        response = self.get_response(request)
        return response


class OrgMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org = get_org_from_request(request)
        request.current_org = org
        set_current_org(org)
        response = self.get_response(request)
        return response
