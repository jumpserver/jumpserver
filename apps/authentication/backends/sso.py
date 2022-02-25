from django.conf import settings

from .base import JMSBaseAuthBackend


class SSOAuthentication(JMSBaseAuthBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_SSO

    def authenticate(self, request, sso_token=None, **kwargs):
        pass


class WeComAuthentication(JMSBaseAuthBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_WECOM

    def authenticate(self, request, **kwargs):
        pass


class DingTalkAuthentication(JMSBaseAuthBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_DINGTALK

    def authenticate(self, request, **kwargs):
        pass


class FeiShuAuthentication(JMSBaseAuthBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_FEISHU

    def authenticate(self, request, **kwargs):
        pass


class AuthorizationTokenAuthentication(JMSBaseAuthBackend):
    """
    什么也不做呀😺
    """
    def authenticate(self, request, **kwargs):
        pass
