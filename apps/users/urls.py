from django.conf.urls import url

from .views import UserListView, UserAddView, UserUpdateView, UserDeleteView, UserDetailView, UserLoginView
from .views import UserGroupListView, UserGroupAddView, UserGroupUpdateView, UserGroupDeleteView, UserGroupDetailView
import api

app_name = 'users'

urlpatterns = [
    url(r'^login/$', UserLoginView.as_view(), name='login'),
    url(r'^users/$', UserListView.as_view(), name='user-list'),
    url(r'^users/(?P<pk>[0-9]+)/$', UserDetailView.as_view(), name='user-detail'),
    url(r'^users/add/$', UserAddView.as_view(), name='user-add'),
    url(r'^users/(?P<pk>[0-9]+)/edit/$', UserUpdateView.as_view(), name='user-edit'),
    url(r'^users/(?P<pk>[0-9]+)/delete/$', UserDeleteView.as_view(), name='user-delete'),
    url(r'^usergroups/$', UserGroupListView.as_view(), name='usergroup-list'),
    url(r'^usergroups/(?P<pk>[0-9]+)/$', UserGroupDetailView.as_view(), name='usergroup-detail'),
    url(r'^usergroups/add/$', UserGroupAddView.as_view(), name='usergroup-add'),
    url(r'^usergroups/(?P<pk>[0-9]+)/edit/$', UserGroupUpdateView.as_view(), name='usergroup-edit'),
    url(r'^usergroups/(?P<pk>[0-9]+)/delete/$', UserGroupDeleteView.as_view(), name='usergroup-delete'),
]


urlpatterns += [
    url(r'^v1/users$', api.UserListAddApi.as_view(), name='user-list-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)$', api.UserDetailDeleteUpdateApi.as_view(), name='user-detail-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)/active$', api.UserActiveApi.as_view(), name='user-active-api'),
    url(r'^v1/usergroups$', api.UserGroupListAddApi.as_view(), name='usergroup-list-api'),
    url(r'^v1/usergroups/(?P<pk>[0-9]+)$', api.UserGroupDetailDeleteUpdateApi.as_view(), name='usergroup-detail-api'),
]
