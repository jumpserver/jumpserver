from django.conf.urls import patterns, include, url


urlpatterns = patterns('jpermission.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^perm_user_list/$', 'perm_user_list'),
)
