from django.conf.urls import url

from .. import views

app_name = 'apply_perms'

urlpatterns = [
    url(r'^apply-permission$', views.ApplyPermissionListView.as_view(),
        name='apply-permission-list'),
    url(r'^apply-permission/create$', views.ApplyPermissionCreateView.as_view(),
        name='apply-permission-create'),
    url(r'^apply-permission/(?P<pk>[0-9]+)/update$', views.ApplyPermissionUpdateView.as_view(),
        name='apply-permission-update'),
    url(r'^apply-permission/(?P<pk>[0-9]+)/delete$', views.ApplyPermissionDeleteView.as_view(),
        name='apply-permission-delete'),
    # url(r'^apply-permission/(?P<pk>[0-9]+)/approve$', views.ApplyPermissionApproveView.as_view(),
    #     name='apply-permission-approve'),
    # url(r'^apply-permission/(?P<pk>[0-9]+)/disapprove$', views.ApplyPermissionDisapproveView.as_view(),
    #     name='apply-permission-disapprove'),
    url(r'^apply-permission/(?P<pk>[0-9]+)$', views.ApplyPermissionDetailView.as_view(),
        name='apply-permission-detail'),
]
