from django.conf.urls import url

from .views import UserListView, UserAddView, UserUpdateView, UserDeleteView, UserDetailView
from .views import UserGroupListView, UserGroupAddView, UserGroupUpdateView, UserGroupDeleteView, UserGroupDetailView
import api

app_name = 'users'

urlpatterns = [
    url(r'^user/$', UserListView.as_view(), name='user-list'),
    url(r'^user/(?P<pk>[0-9]+)/$', UserDetailView.as_view(), name='user-detail'),
    url(r'^user/add/$', UserAddView.as_view(), name='user-add'),
    url(r'^user/(?P<pk>[0-9]+)/edit/$', UserUpdateView.as_view(), name='user-edit'),
    url(r'^user/(?P<pk>[0-9]+)/delete/$', UserDeleteView.as_view(), name='user-delete'),
    url(r'^usergroup/$', UserGroupListView.as_view(), name='usergroup-list'),
    url(r'^usergroup/(?P<pk>[0-9]+)/$', UserGroupDetailView.as_view(), name='usergroup-detail'),
    url(r'^usergroup/add/$', UserGroupAddView.as_view(), name='usergroup-add'),
    url(r'^usergroup/(?P<pk>[0-9]+)/edit/$', UserGroupUpdateView.as_view(), name='usergroup-edit'),
    url(r'^usergroup/(?P<pk>[0-9]+)/delete/$', UserGroupDeleteView.as_view(), name='usergroup-delete'),
]


urlpatterns += [
    url(r'^v1/users/$', api.UserListAddApi.as_view(), name='user-list-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)/$', api.UserDetailDeleteUpdateApi.as_view(), name='user-detail-api'),
    url(r'^v1/usergroups/$', api.UserGroupListAddApi.as_view(), name='usergroup-list-api'),
    url(r'^v1/usergroups/(?P<pk>[0-9]+)/$', api.UserGroupDetailDeleteUpdateApi.as_view(), name='usergroup-detail-api'),
]
