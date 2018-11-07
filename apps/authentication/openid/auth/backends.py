# coding:utf-8
#

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from requests.exceptions import HTTPError

from ..models import OIDC_ACCESS_TOKEN

UserModel = get_user_model()


class BaseOpenIDAuthorizationBackend(object):

    def user_can_authenticate(self, user):
        """
        Reject users with is_active=False. Custom user models that don't have
        that attribute are allowed.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def get_user(self, user_id):
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None


class OpenIDAuthorizationCodeBackend(BaseOpenIDAuthorizationBackend):

    def authenticate(self, request, code, redirect_uri):
        import authentication.openid.services.oidc_profile

        if not hasattr(request, 'client'):
            print('Add BaseOpenIDMiddleware to middlewares')
            return AnonymousUser()

        try:
            oidc_profile = authentication.openid.services.oidc_profile.\
                update_or_create_from_code(
                    client=request.client,
                    code=code,
                    redirect_uri=redirect_uri
                )
        except HTTPError:
            return AnonymousUser()

        # 用于判断openid用户是否单点退出-middleware
        request.session[OIDC_ACCESS_TOKEN] = oidc_profile.access_token

        return oidc_profile.user


class OpenIDAuthorizationCocoBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        pass

