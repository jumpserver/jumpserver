from django.conf.urls import url

from .views import UserListView, UserAddView, UserUpdateView

app_name = 'users'

urlpatterns = [
    url(r'^$', UserListView.as_view(), name='user-list'),
    url(r'^(?P<pk>[0-9]+)/$', UserListView.as_view(), name='user-detail'),
    url(r'^add/$', UserAddView.as_view(), name='user-add'),
    url(r'^(?P<pk>[0-9]+)/edit/$', UserUpdateView.as_view(), name='user-edit'),
    url(r'^(?P<pk>[0-9]+)/delete/$', UserListView.as_view(), name='user-delete'),
]
