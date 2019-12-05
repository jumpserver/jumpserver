# -*- coding: utf-8 -*-
#
import re
import time

from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.views.generic import View
from django.utils.translation import ugettext_lazy as _
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from common.http import HttpResponseTemporaryRedirect


__all__ = [
    'LunaView', 'I18NView', 'KokoView', 'WsView', 'HealthCheckView',
    'redirect_format_api'
]


class LunaView(View):
    def get(self, request):
        msg = _("<div>Luna is a separately deployed program, you need to deploy Luna, koko, configure nginx for url distribution,</div> "
                "</div>If you see this page, prove that you are not accessing the nginx listening port. Good luck.</div>")
        return HttpResponse(msg)


class I18NView(View):
    def get(self, request, lang):
        referer_url = request.META.get('HTTP_REFERER', '/')
        response = HttpResponseRedirect(referer_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        return response


api_url_pattern = re.compile(r'^/api/(?P<app>\w+)/(?P<version>v\d)/(?P<extra>.*)$')


@csrf_exempt
def redirect_format_api(request, *args, **kwargs):
    _path, query = request.path, request.GET.urlencode()
    matched = api_url_pattern.match(_path)
    if matched:
        kwargs = matched.groupdict()
        kwargs["query"] = query
        _path = '/api/{version}/{app}/{extra}?{query}'.format(**kwargs).rstrip("?")
        return HttpResponseTemporaryRedirect(_path)
    else:
        return JsonResponse({"msg": "Redirect url failed: {}".format(_path)}, status=404)


class HealthCheckView(APIView):
    permission_classes = ()

    def get(self, request):
        return JsonResponse({"status": 1, "time": int(time.time())})


class WsView(APIView):
    ws_port = settings.HTTP_LISTEN_PORT + 1

    def get(self, request):
        msg = _("Websocket server run on port: {}, you should proxy it on nginx"
                .format(self.ws_port))
        return JsonResponse({"msg": msg})


class KokoView(View):
    def get(self, request):
        msg = _(
            "<div>Koko is a separately deployed program, you need to deploy Koko, configure nginx for url distribution,</div> "
            "</div>If you see this page, prove that you are not accessing the nginx listening port. Good luck.</div>")
        return HttpResponse(msg)
