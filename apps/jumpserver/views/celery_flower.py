# -*- coding: utf-8 -*-
#
from django.http import HttpResponse
from django.conf import settings
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt

from proxy.views import proxy_view

flower_url = settings.FLOWER_URL

__all__ = ['celery_flower_view']


@csrf_exempt
def celery_flower_view(request, path):
    if not request.user.is_superuser:
        return HttpResponse("Forbidden")
    remote_url = 'http://{}/{}'.format(flower_url, path)
    try:
        response = proxy_view(request, remote_url)
    except Exception as e:
        msg = _("<h1>Flow service unavailable, check it</h1>") + \
              '<br><br> <div>{}</div>'.format(e)
        response = HttpResponse(msg)
    return response

