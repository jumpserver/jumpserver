# coding:utf-8
#

from requests.exceptions import HTTPError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from authentication.openid.models import OIDC_ACCESS_TOKEN

UserModel = get_user_model()


class BaseOpenIDAuthorizationBackend(object):

    @staticmethod
    def user_can_authenticate(user):
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
        import authentication.openid.services.oidt_profile

        if not hasattr(request, 'client'):
            return AnonymousUser()

        try:
            oidt_profile = authentication.openid.services.oidt_profile.\
                update_or_create_from_code(
                    client=request.client,
                    code=code,
                    redirect_uri=redirect_uri
                )
        except HTTPError:
            return AnonymousUser()

        # Check openid user single logout or not with access_token at middleware
        request.session[OIDC_ACCESS_TOKEN] = oidt_profile.access_token

        user = oidt_profile.user

        return user if self.user_can_authenticate(user) else None
