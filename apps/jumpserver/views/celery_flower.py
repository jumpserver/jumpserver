# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from proxy.views import proxy_view

flower_url = settings.FLOWER_URL

__all__ = ['celery_flower_view']


@csrf_exempt
def celery_flower_view(request, path):
    if not request.user.has_perm('ops.view_taskmonitor'):
        return HttpResponse("Forbidden")
    remote_url = 'http://{}/core/flower/{}'.format(flower_url, path)
    try:
        response = proxy_view(request, remote_url)
    except Exception as e:
        msg = _("<h1>Flower service unavailable, check it</h1>") + \
              '<br><br> <div>{}</div>'.format(e)
        response = HttpResponse(msg)
    return response
