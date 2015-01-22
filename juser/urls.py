from django.conf.urls import patterns, include, url


urlpatterns = patterns('juser.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^user_add/$', 'user_add'),
    (r'^user_list/$', 'user_list'),
    (r'^group_add/$', 'group_add'),
    (r'^group_list/$', 'group_list'),
    (r'^user_detail/$', 'user_detail'),
)
