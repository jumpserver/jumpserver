from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.utils.translation import ugettext as _

import views
import api
from .forms import UserLoginForm

app_name = 'users'

urlpatterns = [
    url(r'^login$',
        auth_views.login,
        {'template_name': "users/login.html",
         'authentication_form': UserLoginForm,
         'redirect_authenticated_user': True},
        name='login'),
    url(r'^logout$',
        auth_views.logout,
        {
            "template_name": "common/flash_message_standalone.html",
            "extra_context": {
                'title': _('Logout success'),
                'messages': _('Logout success, return login page'),
                'redirect_url': '/users/login',
                'auto_redirect': True,
            }
        },
        name='logout'),
    url(r'^password/forgot$', views.UserForgotPasswordView.as_view(), name='forgot-password'),
    url(r'^password/forgot/sendmail-success$',
        views.UserForgotPasswordSendmailSuccessView.as_view(), name='forgot-password-sendmail-success'),
    url(r'^password/reset$', views.UserResetPasswordView.as_view(), name='reset-password'),
    url(r'^password/reset/success$', views.UserResetPasswordSuccessView.as_view(),
        name='reset-password-success'),
    url(r'^user$', views.UserListView.as_view(), name='user-list'),
    url(r'^user/(?P<pk>[0-9]+)$', views.UserDetailView.as_view(), name='user-detail'),
    url(r'^user/create$', views.UserCreateView.as_view(), name='user-create'),
    url(r'^user/(?P<pk>[0-9]+)/update$', views.UserUpdateView.as_view(), name='user-update'),
    url(r'^user/(?P<pk>[0-9]+)/delete$', views.UserDeleteView.as_view(), name='user-delete'),
    url(r'^user-group$', views.UserGroupListView.as_view(), name='user-group-list'),
    url(r'^user-group/(?P<pk>[0-9]+)$', views.UserGroupDetailView.as_view(), name='user-group-detail'),
    url(r'^user-group/create$', views.UserGroupCreateView.as_view(), name='user-group-create'),
    url(r'^user-group/(?P<pk>[0-9]+)/update$', views.UserGroupUpdateView.as_view(), name='user-group-update'),
    url(r'^user-group/(?P<pk>[0-9]+)/delete$', views.UserGroupDeleteView.as_view(), name='user-group-delete'),
]


urlpatterns += [
    url(r'^v1/users$', api.UserListAddApi.as_view(), name='user-list-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)$',
        api.UserDetailDeleteUpdateApi.as_view(), name='user-detail-api'),
    url(r'^v1/users/(?P<pk>[0-9]+)/active$', api.UserActiveApi.as_view(), name='user-active-api'),
    url(r'^v1/user-groups$', api.UserGroupListAddApi.as_view(), name='user-group-list-api'),
    url(r'^v1/user-groups/(?P<pk>[0-9]+)$',
        api.UserGroupDetailDeleteUpdateApi.as_view(), name='user-group-detail-api'),
]
