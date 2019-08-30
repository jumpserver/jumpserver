# -*- coding: utf-8 -*-
#

from .utils import current_org, get_org_from_request
from .models import Organization


def org_processor(request):
    context = {
        # 'ADMIN_ORGS': request.user.admin_orgs,
        # 'AUDIT_ORGS': request.user.audit_orgs,
        'ADMIN_OR_AUDIT_ORGS': Organization.get_user_admin_or_audit_orgs(request.user),
        'CURRENT_ORG': get_org_from_request(request),
        # 'HAS_ORG_PERM': current_org.can_admin_by(request.user),
    }
    return context

