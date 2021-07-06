# -*- coding: utf-8 -*-
#

from .utils import get_org_from_request, set_current_org
from rbac.models import RoleBinding


class OrgMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def set_permed_org_if_need(request):
        if request.path.startswith('/api'):
            return
        if not request.user.is_authenticated:
            return

        org = get_org_from_request(request)

        search_org = None if org.is_root() else org
        has_roles = RoleBinding.objects.filter(user=request.user, org=search_org).exists()
        if has_roles:
            return

        roles_bindings = RoleBinding.objects.filter(user=request.user).exclude(org=None)
        if roles_bindings:
            org_id = str(list(roles_bindings.values_list('org_id', flat=True))[0])
            request.session['oid'] = org_id

    def __call__(self, request):
        self.set_permed_org_if_need(request)
        org = get_org_from_request(request)
        request.current_org = org
        set_current_org(org)
        response = self.get_response(request)
        return response
