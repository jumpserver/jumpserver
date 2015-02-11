from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    (r'^$', 'jumpserver.views.index'),
    (r'^skin_config/$', 'jumpserver.views.skin_config'),
    (r'^base/$', 'jumpserver.views.base'),
    (r'^login/$', 'jumpserver.views.login'),
    (r'^logout/$', 'jumpserver.views.logout'),
    (r'^juser/', include('juser.urls')),
    (r'^jasset/', include('jasset.urls')),
    (r'^jlog/', include('jlog.urls')),
    (r'^jperm/', include('jperm.urls')),

)
