from django.conf.urls import patterns, include, url
from django.contrib import admin
from jumpserver import views

urlpatterns = patterns('',
    url(r'^jasset/', include('jasset.urls')),
    url(r'^admin/', include(admin.site.urls)),
    (r'^base/$', views.base),
)
