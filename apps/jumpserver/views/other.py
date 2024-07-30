# -*- coding: utf-8 -*-
#
import re

from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, TemplateView
from rest_framework.views import APIView

from common.utils import lazyproperty
from common.views.http import HttpResponseTemporaryRedirect

__all__ = [
    'LunaView', 'I18NView', 'KokoView', 'WsView',
    'redirect_format_api', 'redirect_old_apps_view', 'UIView',
    'ResourceDownload',
]


class LunaView(View):
    def get(self, request):
        msg = _(
            "<div>Luna is a separately deployed program, you need to deploy Luna, koko, configure nginx for url distribution,</div> "
            "</div>If you see this page, prove that you are not accessing the nginx listening port. Good luck.</div>")
        return HttpResponse(msg)


class I18NView(View):
    def get(self, request, lang):
        referer_url = request.META.get('HTTP_REFERER', '/')
        response = HttpResponseRedirect(referer_url)
        expires = timezone.now() + timezone.timedelta(days=365)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, expires=expires)

        if request.user.is_authenticated:
            request.user.lang = lang
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


@csrf_exempt
def redirect_old_apps_view(request, *args, **kwargs):
    path = request.get_full_path()
    if path.find('/core') != -1:
        raise Http404()
    if path in ['/docs/', '/docs', '/core/docs/', '/core/docs']:
        return redirect('/api/docs/')
    new_path = '/core{}'.format(path)
    return HttpResponseTemporaryRedirect(new_path)


class WsView(APIView):
    ws_port = settings.HTTP_LISTEN_PORT + 1

    def get(self, request):
        msg = _("Websocket server run on port: {}, you should proxy it on nginx"
                .format(self.ws_port))
        return JsonResponse({"msg": msg})


class UIView(View):
    def get(self, request):
        msg = "如果你能看到这个页面，证明你的配置是有问题的，请参考文档设置好nginx, UI由Lina项目提供"
        return HttpResponse(msg)


class KokoView(View):
    def get(self, request):
        msg = _(
            "<div>Koko is a separately deployed program, you need to deploy Koko, configure nginx for url distribution,</div> "
            "</div>If you see this page, prove that you are not accessing the nginx listening port. Good luck.</div>")
        return HttpResponse(msg)


class ResourceDownload(TemplateView):
    template_name = 'resource_download.html'

    @lazyproperty
    def versions_content(self):
        return """
        MRD_VERSION=10.6.7
        OPENSSH_VERSION=v9.4.0.0
        TINKER_VERSION=v0.1.6
        VIDEO_PLAYER_VERSION=0.1.9
        CLIENT_VERSION=v2.1.3
        """

    def get_meta_json(self):
        content = self.versions_content
        lines = content.splitlines()
        meta = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=')
            meta[key] = value
        return meta

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.get_meta_json()
        context.update(meta)
        return context


def csrf_failure(request, reason=""):
    from django.shortcuts import reverse
    login_url = reverse('authentication:login') + '?csrf_failure=1&admin=1'
    return redirect(login_url)
