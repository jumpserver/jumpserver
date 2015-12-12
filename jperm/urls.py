from django.conf.urls import patterns, include, url
from jperm.views import *

urlpatterns = patterns('jperm.views',
                       url(r'^rule/$', perm_rule_list, name='rule_list'),
                       url(r'^perm_rule_add/$', perm_rule_add, name='rule_add'),
                       url(r'^perm_rule_detail/$', perm_rule_detail, name='rule_detail'),
                       url(r'^perm_rule_edit/$', perm_rule_edit, name='rule_edit'),
                       url(r'^perm_rule_delete/$', perm_rule_delete, name='rule_del'),
                       url(r'^role/$', perm_role_list, name='role_list'),
                       url(r'^role/perm_role_add/$', perm_role_add, name='role_add'),
                       url(r'^role/perm_role_delete/$', perm_role_delete, name='role_del'),
                       url(r'^role/perm_role_detail/$', perm_role_detail, name='role_detail'),
                       url(r'^role/perm_role_edit/$', perm_role_edit, name='role_edit'),
                       url(r'^role/push/$', perm_role_push, name='role_push'),
                       url(r'^role/recycle/$', perm_role_recycle, name='role_recycle'),
                       url(r'^role/get/$', perm_role_get, name='role_get'),
                       url(r'^sudo/$', perm_sudo_list, name='sudo_list'),
                       url(r'^sudo/perm_sudo_add/$', perm_sudo_add, name='sudo_add'),
                       url(r'^sudo/perm_sudo_delete/$', perm_sudo_delete, name='sudo_del'),
                       url(r'^sudo/perm_sudo_edit/$', perm_sudo_edit, name='sudo_edit'),
                       )
