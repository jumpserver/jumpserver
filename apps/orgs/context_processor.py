# -*- coding: utf-8 -*-
#

from .utils import current_org, get_current_org
from .models import Organization


def org_processor(request):
    context = {
        'ADMIN_ORGS': Organization.get_user_admin_orgs(request.user),
        'CURRENT_ORG': get_current_org(),
        'HAS_ORG_PERM': current_org.can_admin_by(request.user),
    }
    return context

