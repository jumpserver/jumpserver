from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^skin_config/$', 'jumpserver.views.skin_config'),
    (r'^base/$', 'jumpserver.views.base'),
    (r'^juser/', include('juser.urls')),
    (r'^jperm/', include('jperm.urls')),
    url(r'^jasset/', include('jasset.urls')),
)
