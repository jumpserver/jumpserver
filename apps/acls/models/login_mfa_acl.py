from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import JSONManyToManyField
from common.utils import get_request_ip, get_ip_city, contains_ip
from common.utils.timezone import local_now_display, contains_time_period
from .base import UserBaseACL
from authentication.const import MFAType
from orgs.utils import tmp_to_root_org


class LoginMFAACLManager(models.Manager):
    def get_user_acls(self, user):
        queryset = LoginMFAACL.objects.all()
        q = JSONManyToManyField.get_filter_q(user, 'users')
        queryset = queryset.filter(q)
        return queryset.filter(is_active=True).distinct()


class LoginMFAACL(UserBaseACL):
    # 规则，ip_group, time_period
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))
    # MFA 类型
    mfa_type = models.CharField(
        max_length=32, default=MFAType.OTP,
        choices=MFAType.choices, verbose_name=_('MFA type')
    )

    objects = LoginMFAACLManager()

    class Meta(UserBaseACL.Meta):
        verbose_name = _('Login MFA acl')
        abstract = False

    def __str__(self):
        return self.name

    def is_action(self, action):
        return self.action == action

    @classmethod
    def get_match_rules(cls, user, ip):
        """
        获取匹配用户和 IP 的 MFA ACL 规则
        返回第一个匹配的规则（按优先级排序）
        """
        with tmp_to_root_org():
            acl_qs = cls.get_user_acls(user)

        if not acl_qs:
            return None

        for acl in acl_qs:
            # 检查 reviewer 配置（如果需要）
            if acl.is_action('review') and not acl.reviewers.exists():
                continue

            ip_group = acl.rules.get('ip_group')
            time_periods = acl.rules.get('time_period')

            # 检查 IP 是否匹配
            is_contain_ip = contains_ip(ip, ip_group) if ip_group else True
            # 检查时间段是否匹配
            is_contain_time_period = contains_time_period(time_periods) if time_periods else True

            if is_contain_ip and is_contain_time_period:
                # 满足条件，则返回
                return acl
        return None

    def check_mfa_type(self, user, ip=None):
        """
        检查是否需要应用 MFA 规则
        :param user: 用户对象
        :param ip: 登录 IP
        :return: 如果需要 MFA 验证，返回 mfa_type；否则返回 None
        """
        if not self.is_active:
            return None

        if ip is None:
            ip = '0.0.0.0'

        # 重新验证规则匹配
        matched_acl = self.__class__.get_match_rules(user, ip)
        if not matched_acl:
            return None

        # 返回配置的 MFA 类型
        return matched_acl.mfa_type