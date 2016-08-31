from django.conf.urls import url
from django.contrib.auth import views as auth_views

import views
import api

app_name = 'users'

urlpatterns = [
    url(r'^login$', auth_views.login, {'template_name': 'users/login.html'}, name='login'),
    url(r'^logout$', auth_views.logout, {'template_name': 'users/login.html'}, name='logout'),
    url(r'^password/forget$', views.UserForgetPasswordView.as_view(), name='forget-password'),
    url(r'^password/reset$', views.UserRestPasswordView.as_view(), name='reset-password'),
    url(r'^users$', views.UserListView.as_view(), name='user-list'),
    url(r'^users/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name='user-detail'),
    url(r'^users/add$', views.UserAddView.as_view(), name='user-add'),
    url(r'^users/(?P<pk>[0-9]+)/edit$', views.UserUpdateView.as_view(), name='user-edit'),
    url(r'^users/(?P<pk>[0-9]+)/delete$', views.UserDeleteView.as_view(), name='user-delete'),
    url(r'^usergroups$', views.UserGroupListView.as_view(), name='usergroup-list'),
    url(r'^usergroups/(?P<pk>[0-9]+)$', views.UserGroupDetailView.as_view(), name='usergroup-detail'),
    url(r'^usergroups/add/$', views.UserGroupAddView.as_view(), name='usergroup-add'),
    url(r'^usergroups/(?P<pk>[0-9]+)/edit$', views.UserGroupUpdateView.as_view(), name='usergroup-edit'),
    url(r'^usergroups/(?P<pk>[0-9]+)/delete$', views.UserGroupDeleteView.as_view(), name='usergroup-delete'),
]


urlpatterns += [
    url(r'^v1/users$', api.UserListAddApi.as_view(), name='user-list-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)$', api.UserDetailDeleteUpdateApi.as_view(), name='user-detail-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)/active$', api.UserActiveApi.as_view(), name='user-active-api'),
    url(r'^v1/usergroups$', api.UserGroupListAddApi.as_view(), name='usergroup-list-api'),
    url(r'^v1/usergroups/(?P<pk>[0-9]+)$', api.UserGroupDetailDeleteUpdateApi.as_view(), name='usergroup-detail-api'),
]
