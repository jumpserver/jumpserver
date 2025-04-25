#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as _UserManager
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from common.db import fields, models as jms_models
from common.utils import (
    date_expired_default, get_logger, lazyproperty
)
from labels.mixins import LabeledMixin
from orgs.utils import current_org
from ._auth import AuthMixin, MFAMixin
from ._face import FaceMixin
from ._json import JSONFilterMixin
from ._role import RoleMixin, SystemRoleManager, OrgRoleManager
from ._source import SourceMixin, Source
from ._token import TokenMixin

logger = get_logger(__file__)
__all__ = [
    "User",
    "UserPasswordHistory",
    "MFAMixin",
    "AuthMixin",
    "FaceMixin",
    "RoleMixin"
]


class UserManager(_UserManager):
    def get_by_natural_key(self, username_or_mail):
        q = models.Q(username=username_or_mail) | models.Q(email=username_or_mail)
        user = self.filter(q).first()
        if not user:
            raise self.model.DoesNotExist
        return user


class User(
    AuthMixin,
    SourceMixin,
    TokenMixin,
    RoleMixin,
    MFAMixin,
    FaceMixin,
    LabeledMixin,
    JSONFilterMixin,
    AbstractUser,
):
    """
    User model, used for authentication and authorization. User can join multiple groups.
    User can have multiple roles, and each role can have multiple permissions.
    User can connect to multiple assets, If he has the permission. Permission was defined in Asset Permission.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(max_length=128, unique=True, verbose_name=_("Username"))
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    email = models.EmailField(max_length=128, unique=True, verbose_name=_("Email"))
    groups = models.ManyToManyField(
        "users.UserGroup",
        related_name="users",
        blank=True,
        verbose_name=_("User group"),
    )
    role = models.CharField(
        default="User", max_length=10, blank=True, verbose_name=_("Role")
    )
    is_service_account = models.BooleanField(
        default=False, verbose_name=_("Is service account")
    )
    avatar = models.ImageField(upload_to="avatar", null=True, verbose_name=_("Avatar"))
    wechat = fields.EncryptCharField(
        max_length=128, blank=True, verbose_name=_("Wechat")
    )
    phone = fields.EncryptCharField(
        max_length=128, blank=True, null=True, verbose_name=_("Phone")
    )
    mfa_level = models.SmallIntegerField(
        default=0, choices=MFAMixin.MFA_LEVEL_CHOICES, verbose_name=_("MFA")
    )
    otp_secret_key = fields.EncryptCharField(
        max_length=128, blank=True, null=True, verbose_name=_("OTP secret key")
    )
    # Todo: Auto generate key, let user download
    private_key = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_("Private key")
    )
    public_key = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_("Public key")
    )
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))
    is_first_login = models.BooleanField(default=True, verbose_name=_("Is first login"))
    date_expired = models.DateTimeField(
        default=date_expired_default,
        blank=True,
        null=True,
        db_index=True,
        verbose_name=_("Date expired"),
    )
    created_by = models.CharField(
        max_length=30, default="", blank=True, verbose_name=_("Created by")
    )
    updated_by = models.CharField(
        max_length=30, default="", blank=True, verbose_name=_("Updated by")
    )
    date_password_last_updated = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        verbose_name=_("Date password last updated"),
    )
    need_update_password = models.BooleanField(
        default=False, verbose_name=_("Need update password")
    )
    source = models.CharField(
        max_length=30,
        default=Source.local,
        choices=Source.choices,
        verbose_name=_("Source"),
    )
    wecom_id = models.CharField(
        null=True, default=None, max_length=128, verbose_name=_("WeCom")
    )
    dingtalk_id = models.CharField(
        null=True, default=None, max_length=128, verbose_name=_("DingTalk")
    )
    feishu_id = models.CharField(
        null=True, default=None, max_length=128, verbose_name=_("FeiShu")
    )
    lark_id = models.CharField(
        null=True, default=None, max_length=128, verbose_name="Lark"
    )
    slack_id = models.CharField(
        null=True, default=None, max_length=128, verbose_name=_("Slack")
    )
    face_vector = fields.EncryptTextField(
        null=True, blank=True, max_length=2048, verbose_name=_("Face Vector")
    )
    date_api_key_last_used = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Date api key used")
    )
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    objects = UserManager()
    DATE_EXPIRED_WARNING_DAYS = 5

    def __str__(self):
        return "{0.name}({0.username})".format(self)

    @classmethod
    def get_queryset(cls):
        queryset = cls.objects.all()
        if not current_org.is_root():
            queryset = current_org.get_members()
        queryset = queryset.exclude(is_service_account=True)
        return queryset

    @property
    def secret_key(self):
        instance = self.preferences.filter(name="secret_key").first()
        if not instance:
            return
        return instance.decrypt_value

    @property
    def receive_backends(self):
        try:
            return self.user_msg_subscription.receive_backends
        except:
            return []

    @property
    def is_otp_secret_key_bound(self):
        return bool(self.otp_secret_key)

    def get_absolute_url(self):
        return reverse("users:user-detail", args=(self.id,))

    @property
    def is_expired(self):
        if self.date_expired and self.date_expired < timezone.now():
            return True
        else:
            return False

    def is_password_authenticate(self):
        cas = self.Source.cas
        saml2 = self.Source.saml2
        oauth2 = self.Source.oauth2
        openid = self.Source.openid
        return self.source not in [cas, saml2, oauth2, openid]

    @property
    def expired_remain_days(self):
        date_remain = self.date_expired - timezone.now()
        return date_remain.days

    @property
    def will_expired(self):
        if 0 <= self.expired_remain_days <= self.DATE_EXPIRED_WARNING_DAYS:
            return True
        else:
            return False

    @property
    def lang(self):
        return self.preference.get_value("lang")

    @lang.setter
    def lang(self, value):
        self.preference.set_value('lang', value)

    @property
    def preference(self):
        from users.models.preference import PreferenceManager
        return PreferenceManager(self)

    @property
    def is_valid(self):
        if self.is_active and not self.is_expired:
            return True
        return False

    def set_required_attr_if_need(self):
        if not self.name:
            self.name = self.username
        if not self.email or "@" not in self.email:
            email = "{}@{}".format(self.username, settings.EMAIL_SUFFIX)
            if "@" in self.username:
                email = self.username
            self.email = email

    def save(self, *args, **kwargs):
        self.set_required_attr_if_need()
        if self.username == "admin":
            self.role = "Admin"
            self.is_active = True
        return super().save(*args, **kwargs)

    def is_member_of(self, user_group):
        if user_group in self.groups.all():
            return True
        return False

    def set_avatar(self, f):
        self.avatar.save(self.username, f)

    @classmethod
    def get_avatar_url(cls, username):
        user_default = settings.STATIC_URL + "img/avatar/user.png"
        return user_default

    def avatar_url(self):
        admin_default = settings.STATIC_URL + "img/avatar/admin.png"
        user_default = settings.STATIC_URL + "img/avatar/user.png"
        if self.avatar:
            return self.avatar.url
        if self.is_superuser:
            return admin_default
        else:
            return user_default

    def unblock_login(self):
        from users.utils import LoginBlockUtil, MFABlockUtils

        LoginBlockUtil.unblock_user(self.username)
        MFABlockUtils.unblock_user(self.username)

    @lazyproperty
    def login_blocked(self):
        from users.utils import LoginBlockUtil, MFABlockUtils

        if LoginBlockUtil.is_user_block(self.username):
            return True
        if MFABlockUtils.is_user_block(self.username):
            return True
        return False

    def delete(self, using=None, keep_parents=False):
        if self.pk == 1 or self.username == "admin":
            raise PermissionDenied(_("Can not delete admin user"))
        return super(User, self).delete(using=using, keep_parents=keep_parents)

    class Meta:
        ordering = ["username"]
        verbose_name = _("User")
        unique_together = (
            ("dingtalk_id",),
            ("wecom_id",),
            ("feishu_id",),
            ("lark_id",),
            ("slack_id",),
        )
        permissions = [
            ("invite_user", _("Can invite user")),
            ("remove_user", _("Can remove user")),
            ("match_user", _("Can match user")),
        ]

    def can_send_created_mail(self):
        if self.email and self.source == self.Source.local.value:
            return True
        return False


class UserPasswordHistory(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    password = models.CharField(max_length=128)
    user = models.ForeignKey(
        "users.User",
        related_name="history_passwords",
        on_delete=jms_models.CASCADE_SIGNAL_SKIP,
        verbose_name=_("User"),
    )
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Date created")
    )

    def __str__(self):
        return f"{self.user} set at {self.date_created}"

    def __repr__(self):
        return self.__str__()

    class Meta:
        verbose_name = _("User password history")
