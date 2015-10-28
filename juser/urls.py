from django.conf.urls import patterns, include, url
from jumpserver.api import view_splitter
from juser.views import *

urlpatterns = patterns('juser.views',
    # Examples:
    # url(r'^$', 'jumpserver.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    (r'^group_add/$', group_add),
    (r'^group_list/$', group_list),
    (r'^group_del/$', group_del),
    (r'^group_edit/$', group_edit),
    (r'^user_add/$', user_add),
    (r'^user_list/$', user_list),
    (r'^send_mail_retry/$', send_mail_retry),
    (r'^reset_password/$', reset_password),
    (r'^forget_password/$', forget_password),
    (r'^user_detail/$', 'user_detail'),
    (r'^user_del/$', 'user_del'),
    (r'^user_edit/$', user_edit),
    (r'^profile/$', 'profile'),
    (r'^change_info/$', 'change_info'),
    (r'^regen_ssh_key/$', 'regen_ssh_key'),
    (r'^change_role/$', 'chg_role'),
    (r'^down_key/$', 'down_key'),
)
