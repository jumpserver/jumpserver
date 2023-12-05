from django.conf import settings

from .base import JMSModelBackend


class SSOAuthentication(JMSModelBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_SSO

    def authenticate(self, request, sso_token=None, **kwargs):
        pass


class WeComAuthentication(JMSModelBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_WECOM

    def authenticate(self, request, **kwargs):
        pass


class DingTalkAuthentication(JMSModelBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_DINGTALK

    def authenticate(self, request, **kwargs):
        pass


class FeiShuAuthentication(JMSModelBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_FEISHU

    def authenticate(self, request, **kwargs):
        pass


class SlackAuthentication(JMSModelBackend):
    """
    什么也不做呀😺
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_SLACK

    def authenticate(self, request, **kwargs):
        pass


class AuthorizationTokenAuthentication(JMSModelBackend):
    """
    什么也不做呀😺
    """
    def authenticate(self, request, **kwargs):
        pass
