from __future__ import absolute_import

from django.conf.urls import url

from .. import views

app_name = 'users'

urlpatterns = [
    # Login view
    url(r'^login$', views.UserLoginView.as_view(), name='login'),
    url(r'^logout$', views.UserLogoutView.as_view(), name='logout'),
    url(r'^password/forgot$', views.UserForgotPasswordView.as_view(),
        name='forgot-password'),
    url(r'^password/forgot/sendmail-success$',
        views.UserForgotPasswordSendmailSuccessView.as_view(),
        name='forgot-password-sendmail-success'),
    url(r'^password/reset$', views.UserResetPasswordView.as_view(),
        name='reset-password'),
    url(r'^password/reset/success$',
        views.UserResetPasswordSuccessView.as_view(),
        name='reset-password-success'),

    # Profile
    url(r'^profile/$', views.UserProfileView.as_view(),
        name='user-profile'),
    url(r'^profile/update/$', views.UserProfileUpdateView.as_view(),
        name='user-profile-update'),
    url(r'^profile/password/update/$', views.UserPasswordUpdateView.as_view(),
        name='user-password-update'),
    url(r'^profile/pubkey/update/$',
        views.UserPublicKeyUpdateView.as_view(),
        name='user-pubkey-update'),

    # User view
    url(r'^user$', views.UserListView.as_view(), name='user-list'),
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(),
        name='user-detail'),
    url(r'^user/(?P<pk>[0-9]+)/asset-permission$',
        views.UserAssetPermissionView.as_view(),
        name='user-asset-permission'),
    url(r'^user/(?P<pk>[0-9]+)/asset-permission/create$',
        views.UserAssetPermissionCreateView.as_view(),
        name='user-asset-permission-create'),
    url(r'^user/(?P<pk>[0-9]+)/assets',
        views.UserGrantedAssetView.as_view(),
        name='user-granted-asset'),
    url(r'^user/(?P<pk>[0-9]+)/login-history', views.UserDetailView.as_view(),
        name='user-login-history'),
    url(r'^user/export/', views.UserExportView.as_view(),
        name='user-export'),
    url(r'^first-login/$', views.UserFirstLoginView.as_view(),
        name='user-first-login'),
    url(r'^user/import/$', views.UserBulkImportView.as_view(),
        name='user-import'),
    url(r'^user/create$', views.UserCreateView.as_view(),
        name='user-create'),
    url(r'^user/(?P<pk>[0-9]+)/update$', views.UserUpdateView.as_view(),
        name='user-update'),
    url(r'^user/update$', views.UserBulkUpdateView.as_view(),
        name='user-bulk-update'),

    # User group view
    url(r'^user-group$', views.UserGroupListView.as_view(),
        name='user-group-list'),
    url(r'^user-group/(?P<pk>[0-9]+)$', views.UserGroupDetailView.as_view(),
        name='user-group-detail'),
    url(r'^user-group/create$', views.UserGroupCreateView.as_view(),
        name='user-group-create'),
    url(r'^user-group/(?P<pk>[0-9]+)/update$', views.UserGroupUpdateView.as_view(),
        name='user-group-update'),
    url(r'^user-group/(?P<pk>[0-9]+)/asset-permission$',
        views.UserGroupAssetPermissionView.as_view(),
        name='user-group-asset-permission'),
    url(r'^user-group/(?P<pk>[0-9]+)/asset-permission/create$',
        views.UserGroupAssetPermissionCreateView.as_view(),
        name='user-group-asset-permission-create'),
    url(r'^user-group/(?P<pk>[0-9]+)/assets',
        views.UserGroupGrantedAssetView.as_view(),
        name='user-group-granted-asset'),
]
