from django.conf import settings

from .base import JMSBaseAuthBackend


class SSOAuthentication(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_SSO

    def authenticate(self):
        pass


class WeComAuthentication(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_WECOM

    def authenticate(self):
        pass


class DingTalkAuthentication(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_DINGTALK

    def authenticate(self):
        pass


class FeiShuAuthentication(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_FEISHU

    def authenticate(self):
        pass


class LarkAuthentication(FeiShuAuthentication):
    @staticmethod
    def is_enabled():
        return settings.AUTH_LARK


class SlackAuthentication(JMSBaseAuthBackend):
    @staticmethod
    def is_enabled():
        return settings.AUTH_SLACK

    def authenticate(self):
        pass


class AuthorizationTokenAuthentication(JMSBaseAuthBackend):
    def authenticate(self):
        pass
