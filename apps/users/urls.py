from django.conf.urls import url

import views
import api

app_name = 'users'

urlpatterns = [
    url(r'^login$', views.UserLoginView.as_view(), name='login'),
    url(r'^logout$', views.UserLogoutView.as_view(), name='logout'),
    url(r'^password/forgot$', views.UserForgotPasswordView.as_view(), name='forgot-password'),
    url(r'^password/forgot/sendmail-success$',
        views.UserForgotPasswordSendmailSuccessView.as_view(), name='forgot-password-sendmail-success'),
    url(r'^password/reset$', views.UserResetPasswordView.as_view(), name='reset-password'),
    url(r'^password/reset/success$', views.UserResetPasswordSuccessView.as_view(),
        name='reset-password-success'),
    url(r'^user$', views.UserListView.as_view(), name='user-list'),
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name='user-detail'),
    url(r'^user/(?P<pk>[0-9]+)/asset-permission$', views.UserAssetPermissionView.as_view(),
        name='user-asset-permission'),
    url(r'^user/(?P<pk>[0-9]+)/asset-permission/create$', views.UserAssetPermissionCreateView.as_view(),
        name='user-asset-permission-create'),
    url(r'^user/(?P<pk>[0-9]+)/granted-asset', views.UserGrantedAssetView.as_view(), name='user-granted-asset'),
    url(r'^user/(?P<pk>[0-9]+)/login-history', views.UserDetailView.as_view(), name='user-login-history'),
    url(r'^first-login/$', views.UserFirstLoginView.as_view(), name='user-first-login'),
    url(r'^import/$', views.BulkImportUserView.as_view(), name='user-import'),
    url(r'^user/(?P<pk>[0-9]+)/assets-perm$', views.UserDetailView.as_view(), name='user-detail'),
    url(r'^user/create$', views.UserCreateView.as_view(), name='user-create'),
    url(r'^user/(?P<pk>[0-9]+)/update$', views.UserUpdateView.as_view(), name='user-update'),
    url(r'^user-group$', views.UserGroupListView.as_view(), name='user-group-list'),
    url(r'^user-group/(?P<pk>[0-9]+)$', views.UserGroupDetailView.as_view(), name='user-group-detail'),
    url(r'^user-group/create$', views.UserGroupCreateView.as_view(), name='user-group-create'),
    url(r'^user-group/(?P<pk>[0-9]+)/update$', views.UserGroupUpdateView.as_view(), name='user-group-update'),
]


urlpatterns += [
    url(r'^v1/users$', api.UserListAddApi.as_view(), name='user-list-api'),
    url(r'^v1/users/update/$', api.UserBulkUpdateApi.as_view(), name='user-bulk-update-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)$',
        api.UserDetailDeleteUpdateApi.as_view(), name='user-detail-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)/patch$',
        api.UserAttributeApi.as_view(), name='user-patch-api'),
    url(r'^v1/users/(?P<pk>\d+)/reset-password/$', api.UserResetPasswordApi.as_view(), name='user-reset-password-api'),
    url(r'^v1/users/(?P<pk>\d+)/reset-pk/$', api.UserResetPKApi.as_view(), name='user-reset-pk-api'),
    url(r'^v1/users/(?P<pk>\d+)/update-pk/$', api.UserUpdatePKApi.as_view(), name='user-update-pk-api'),
    url(r'^v1/user-groups$', api.UserGroupListAddApi.as_view(), name='user-group-list-api'),
    url(r'^v1/user-groups/(?P<pk>[0-9]+)$',
        api.UserGroupDetailDeleteUpdateApi.as_view(), name='user-group-detail-api'),
    url(r'^v1/user-groups/(?P<pk>\d+)/user/(?P<uid>\d+)/$',
        api.DeleteUserFromGroupApi.as_view(), name='delete-user-from-group-api'),
    url(r'^v1/user-groups/(?P<pk>[0-9]+)/users/$',
        api.GroupUserEditApi.as_view(), name='group-user-edit-api'),
    url(r'^v1/user-groups/(?P<pk>[0-9]+)/edit/$', api.GroupEditApi.as_view(),
        name='user-group-edit-api'),
]
