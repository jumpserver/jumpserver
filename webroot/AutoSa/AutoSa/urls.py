from django.conf.urls import patterns, include, url

from django.contrib import admin
from AutoSa import views
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'AutoSa.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    (r'^install/', views.install),
    (r'^$', views.index),
    (r'^login/$', views.login),
    (r'^logout/$', views.logout),
    (r'^showUser/$', views.showUser),
    (r'^addUser/$', views.addUser),
    (r'^showAssets/$', views.showAssets),
    (r'^addAssets/$', views.addAssets),
    (r'^showPerm/$', views.showPerm),
    (r'^addPerm/$', views.addPerm),
    (r'^downKey/$', views.downKey),
    (r'^chgPass/$', views.chgPass),
    (r'^chgKey/$', views.chgKey),
)
