from django.conf.urls import patterns, include, url


urlpatterns = patterns('juser.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),


    (r'^dept_list/$', 'dept_list'),
    (r'^dept_add/$', 'dept_add'),
    (r'^dept_del/$', 'dept_del'),
    (r'^dept_detail/$', 'dept_detail'),
    (r'^dept_del_ajax/$', 'dept_del_ajax'),
    (r'^dept_edit/$', 'dept_edit'),
    (r'^group_add/$', 'group_add'),
    (r'^group_list/$', 'group_list'),
    (r'^group_detail/$', 'group_detail'),
    (r'^group_del/$', 'group_del'),
    (r'^group_del_ajax/$', 'group_del_ajax'),
    (r'^group_edit/$', 'group_edit'),
    (r'^user_add/$', 'user_add'),
    (r'^user_list/(?P<option>\w*)/?$', 'user_list'),
    (r'^user_detail/$', 'user_detail'),
    (r'^user_del/$', 'user_del'),
    (r'^user_del_ajax/$', 'user_del_ajax'),
    (r'^user_edit/$', 'user_edit'),
    (r'^profile/$', 'profile'),
    (r'^chg_pass/$', 'chg_pass'),
)
