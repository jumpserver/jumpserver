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
from django.http import HttpResponseRedirect


urlpatterns = [
    url(r'^captcha/', include('captcha.urls')),
    url(r'^$', TemplateView.as_view(template_name='base.html'), name='index'),
    url(r'^(api/)?users/', include('users.urls')),
    url(r'^assets/', include('assets.urls')),
    url(r'^perms/', include('perms.urls')),
    url(r'^terminal/', include('webterminal.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

