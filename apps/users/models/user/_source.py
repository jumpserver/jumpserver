#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Source(models.TextChoices):
    local = "local", _("Local")
    ldap = "ldap", "LDAP/AD"
    ldap_ha = "ldap_ha", "LDAP/AD (HA)"
    openid = "openid", "OpenID"
    radius = "radius", "Radius"
    cas = "cas", "CAS"
    saml2 = "saml2", "SAML2"
    oauth2 = "oauth2", "OAuth2"
    wecom = "wecom", _("WeCom")
    dingtalk = "dingtalk", _("DingTalk")
    feishu = "feishu", _("FeiShu")
    lark = "lark", _("Lark")
    slack = "slack", _("Slack")
    custom = "custom", "Custom"


class SourceMixin:
    source: str
    _source_choices = []
    Source = Source

    SOURCE_BACKEND_MAPPING = {
        Source.local: [
            settings.AUTH_BACKEND_MODEL,
            settings.AUTH_BACKEND_PUBKEY,
        ],
        Source.ldap: [settings.AUTH_BACKEND_LDAP],
        Source.openid: [
            settings.AUTH_BACKEND_OIDC_PASSWORD,
            settings.AUTH_BACKEND_OIDC_CODE,
        ],
        Source.radius: [settings.AUTH_BACKEND_RADIUS],
        Source.cas: [settings.AUTH_BACKEND_CAS],
        Source.saml2: [settings.AUTH_BACKEND_SAML2],
        Source.oauth2: [settings.AUTH_BACKEND_OAUTH2],
        Source.wecom: [settings.AUTH_BACKEND_WECOM],
        Source.feishu: [settings.AUTH_BACKEND_FEISHU],
        Source.lark: [settings.AUTH_BACKEND_LARK],
        Source.slack: [settings.AUTH_BACKEND_SLACK],
        Source.dingtalk: [settings.AUTH_BACKEND_DINGTALK],
        Source.custom: [settings.AUTH_BACKEND_CUSTOM],
    }

    @classmethod
    def get_sources_enabled(cls):
        mapper = {
            cls.Source.local: True,
            cls.Source.ldap: settings.AUTH_LDAP,
            cls.Source.ldap_ha: settings.AUTH_LDAP_HA,
            cls.Source.openid: settings.AUTH_OPENID,
            cls.Source.radius: settings.AUTH_RADIUS,
            cls.Source.cas: settings.AUTH_CAS,
            cls.Source.saml2: settings.AUTH_SAML2,
            cls.Source.oauth2: settings.AUTH_OAUTH2,
            cls.Source.wecom: settings.AUTH_WECOM,
            cls.Source.feishu: settings.AUTH_FEISHU,
            cls.Source.slack: settings.AUTH_SLACK,
            cls.Source.dingtalk: settings.AUTH_DINGTALK,
            cls.Source.custom: settings.AUTH_CUSTOM,
        }
        return [str(k) for k, v in mapper.items() if v]

    @property
    def source_display(self):
        return self.get_source_display()

    @property
    def is_local(self):
        return self.source == self.Source.local.value

    @classmethod
    def get_source_choices(cls):
        if cls._source_choices:
            return cls._source_choices
        used = (
            cls.objects.values_list("source", flat=True).order_by("source").distinct()
        )
        enabled_sources = cls.get_sources_enabled()
        _choices = []
        for k, v in cls.Source.choices:
            if k in enabled_sources or k in used:
                _choices.append((k, v))
        cls._source_choices = _choices
        return cls._source_choices

    @classmethod
    def get_user_allowed_auth_backend_paths(cls, username):
        if not settings.ONLY_ALLOW_AUTH_FROM_SOURCE or not username:
            return None
        user = cls.objects.filter(username=username).first()
        if not user:
            return None
        return user.get_allowed_auth_backend_paths()

    def get_allowed_auth_backend_paths(self):
        if not settings.ONLY_ALLOW_AUTH_FROM_SOURCE:
            return None
        return self.SOURCE_BACKEND_MAPPING.get(self.source, [])
