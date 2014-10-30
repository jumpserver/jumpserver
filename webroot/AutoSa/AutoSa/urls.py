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
    (r'^chgUser/$', views.chgUser),
    (r'^showGroup/$', views.showGroup),
    (r'^addGroup/$', views.addGroup),
    (r'^chgGroup/$', views.chgGroup),
    (r'^showSudo/$', views.showSudo),
    (r'^chgSudo/$', views.chgSudo),
    (r'^showAssets/$', views.showAssets),
    (r'^addAssets/$', views.addAssets),
    (r'^showPerm/$', views.showPerm),
    (r'^addPerm/$', views.addPerm),
    (r'^downKey/$', views.downKey),
    (r'^chgPass/$', views.chgPass),
    (r'^chgKey/$', views.chgKey),
    (r'^upFile/$', views.upFile),
    (r'^downFile/$', views.downFile),
)
