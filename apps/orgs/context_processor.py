# -*- coding: utf-8 -*-
#

from .utils import get_org_from_request


def org_processor(request):
    context = {
        'CURRENT_ORG': get_org_from_request(request),
    }
    return context

