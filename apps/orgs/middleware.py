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
        if not request.user.is_org_admin and not request.user.is_org_auditor:
            return
        org = get_org_from_request(request)
        if org.can_admin_by(request.user):
            return
        if org.can_audit_by(request.user):
            return
        admin_orgs = Organization.get_user_admin_orgs(request.user)
        if admin_orgs:
            request.session['oid'] = str(admin_orgs[0].id)
        audit_orgs = Organization.get_user_audit_orgs(request.user)
        if audit_orgs:
            request.session['oid'] = str(audit_orgs[0].id)

    def __call__(self, request):
        self.set_permed_org_if_need(request)
        org = get_org_from_request(request)
        if org is not None:
            request.current_org = org
            set_current_org(org)
        response = self.get_response(request)
        return response
