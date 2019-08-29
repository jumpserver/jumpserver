# -*- coding: utf-8 -*-
#

from .models import Organization
from .utils import get_org_from_request, set_current_org


class OrgMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def set_permed_org_if_need(request):
        if request.path.startswith('/api'):
            return
        if not request.user.is_authenticated:
            return
        if request.user.is_common_user:
            return
        org = get_org_from_request(request)
        if org.can_admin_by(request.user):
            return
        if org.can_audit_by(request.user):
            return
        admin_orgs = request.user.admin_orgs
        if admin_orgs:
            request.session['oid'] = str(admin_orgs[0].id)
            return
        audit_orgs = request.user.audit_orgs
        if audit_orgs:
            request.session['oid'] = str(audit_orgs[0].id)
            return

    def __call__(self, request):
        self.set_permed_org_if_need(request)
        org = get_org_from_request(request)
        if org is not None:
            request.current_org = org
            set_current_org(org)
        response = self.get_response(request)
        return response
