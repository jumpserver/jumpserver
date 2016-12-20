# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

"""jumpserver URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import TemplateView


urlpatterns = [
    url(r'^captcha/', include('captcha.urls')),
    url(r'^$', TemplateView.as_view(template_name='base.html'), name='index'),
    url(r'^users/', include('users.urls.views_urls', namespace='users')),
    url(r'^assets/', include('assets.urls.views_urls', namespace='assets')),
    url(r'^perms/', include('perms.urls.views_urls', namespace='perms')),
    url(r'^audits/', include('audits.urls.views_urls', namespace='audits')),
    url(r'^terminal/', include('terminal.urls.views_urls', namespace='terminal')),
    url('^ops/', include('ops.urls.view_urls', namespace='ops')),

    url(r'^api/users/', include('users.urls.api_urls', namespace='api-users')),
    url(r'^api/assets/', include('assets.urls.api_urls', namespace='api-assets')),
    url(r'^api/perms/', include('perms.urls.api_urls', namespace='api-perms')),
    url(r'^api/audits/', include('audits.urls.api_urls', namespace='api-audits')),
    url(r'^api/terminal/', include('terminal.urls.api_urls', namespace='api-terminal')),
    url(r'^api/ops/', include('ops.urls.api_urls', namespace='api-ops')),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

