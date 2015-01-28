from django.conf.urls import patterns, include, url


urlpatterns = patterns('jperm.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^perm_edit/$', 'perm_edit'),
    (r'^perm_user_show/$', 'perm_user_show'),
    (r'^perm_list/$', 'perm_list'),
)
