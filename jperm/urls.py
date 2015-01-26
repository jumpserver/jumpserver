from django.conf.urls import patterns, include, url


urlpatterns = patterns('jperm.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^perm_host/$', 'perm_host'),
    (r'^perm_add/$', 'perm_add'),
    (r'^perm_user_show/$', 'perm_user_show'),
    (r'^perm_host/$', 'perm_list'),
    (r'^perm_user_edit/$', 'perm_user_edit'),
    (r'^perm_user_detail/$', 'perm_user_detail'),
    (r'^perm_group_edit/$', 'perm_group_edit'),
    (r'^perm_group_detail/$', 'perm_group_detail'),
)
