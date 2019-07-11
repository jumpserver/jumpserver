# -*- coding: utf-8 -*-
#
from django.views.decorators.csrf import csrf_exempt

from common.http import HttpResponseTemporaryRedirect

__all__ = ["redirect_format_api"]


@csrf_exempt
def redirect_format_api(request, *args, **kwargs):
    resource = kwargs.get("resource", "")
    full_path = request.get_full_path()
    full_path = full_path.replace(resource, resource+"s", 1)
    print("resirect to: {}".format(full_path))
    return HttpResponseTemporaryRedirect(full_path)
