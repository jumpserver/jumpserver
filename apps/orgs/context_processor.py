# -*- coding: utf-8 -*-
#

from .utils import current_org, get_org_from_request
from .models import Organization


def org_processor(request):
    context = {
        # 'ADMIN_ORGS': request.user.admin_orgs,
        # 'AUDIT_ORGS': request.user.audit_orgs,
        'ADMIN_OR_AUDIT_ORGS': request.user.admin_or_audit_orgs,
        'CURRENT_ORG': get_org_from_request(request),
        'HAS_ORG_PERM': request.user.can_admin_current_org,
    }
    return context

