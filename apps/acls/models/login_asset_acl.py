from hashlib import sha256
from dataclasses import dataclass

from django.core.cache import cache
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from accounts.const import AliasAccount
from common.exceptions import JMSException
from common.utils import contains_ip
from common.utils.timezone import contains_time_period
from ..const import ActionChoices

from common.utils import get_logger
from orgs.utils import tmp_to_org
from .base import UserAssetAccountBaseACL

logger = get_logger(__name__)


class LoginAssetACL(UserAssetAccountBaseACL):
    action = models.CharField(
        max_length=64, default=ActionChoices.reject,
        choices=((ActionChoices.accept, _('Accept')), (ActionChoices.reject, _('Reject'))),
        verbose_name=_('Action'),
    )
    reason_enabled = models.BooleanField(default=False, verbose_name=_('Connection reason'))
    mfa_enabled = models.BooleanField(default=False, verbose_name=_('MFA verification'))
    review_enabled = models.BooleanField(default=False, verbose_name=_('Review'))
    notice_enabled = models.BooleanField(default=False, verbose_name=_('Notify'))
    face_verify_enabled = models.BooleanField(default=False, verbose_name=_('Face verify'))
    face_online_enabled = models.BooleanField(default=False, verbose_name=_('Face online'))
    push_account_enabled = models.BooleanField(default=False, verbose_name=_('Push account'))
    change_secret_enabled = models.BooleanField(default=False, verbose_name=_('Secret rotation'))
    recipients = models.ManyToManyField('users.User', related_name='asset_acl_notifications', blank=True, verbose_name=_('Recipients'))

    CONTROL_FIELDS = (
        'reason_enabled', 'mfa_enabled', 'review_enabled', 'notice_enabled',
        'face_verify_enabled', 'face_online_enabled', 'push_account_enabled',
        'change_secret_enabled',
    )

    @classmethod
    def get_stage_fields(cls):
        return {
            'before': ('reason_enabled', 'mfa_enabled', 'face_verify_enabled',
                       'review_enabled', 'push_account_enabled', 'notice_enabled'),
            'online': ('face_online_enabled',),
            'after': ('change_secret_enabled',),
        }

    @staticmethod
    def is_same_account(user, account=None, account_username=None):
        if account is not None and getattr(account, 'alias', None) == AliasAccount.INPUT:
            return False
        username = account_username or getattr(account, 'username', '')
        return username == AliasAccount.USER or username == user.username

    @classmethod
    def _get_filter_queryset(cls, user=None, asset=None, account=None, account_username=None, **kwargs):
        queryset = super()._get_filter_queryset(user=user, asset=asset, **kwargs)
        username = account_username or getattr(account, 'username', '')
        if not username:
            return queryset
        if username == AliasAccount.USER and user:
            username = user.username
        query = models.Q(accounts__contains=username) | models.Q(accounts__contains='*') | models.Q(accounts__contains='@ALL')
        if user and cls.is_same_account(user, account, account_username or username):
            query |= models.Q(accounts__contains=AliasAccount.USER.value)
        return queryset.filter(query)

    @classmethod
    def get_match_rule_acls(cls, user, ip, acl_qs=None):
        queryset = acl_qs if acl_qs is not None else cls.get_user_acls(user)
        if hasattr(queryset, 'prefetch_related'):
            queryset = queryset.order_by('priority', 'name', 'id').prefetch_related('reviewers', 'recipients').iterator(chunk_size=200)
        else:
            queryset = sorted(queryset, key=lambda rule: (rule.priority, rule.name, str(rule.id)))
        matched = []
        priority = None
        for acl in queryset:
            if not acl.is_active:
                continue
            if priority is not None and acl.priority != priority:
                break
            if acl.rules.get('ip_group') and not contains_ip(ip, acl.rules['ip_group']):
                continue
            if acl.rules.get('time_period') and not contains_time_period(acl.rules['time_period']):
                continue
            if priority is None:
                priority = acl.priority
            matched.append(acl)
        return LoginAssetPolicy(tuple(matched)) if matched else None

    @staticmethod
    def filter_available_reviewers(reviewers, org_id):
        from orgs.models import Organization

        reviewers = list(reviewers)
        org = Organization.get_instance(org_id)
        if not org or not reviewers:
            return []
        member_ids = set(org.get_members().filter(pk__in=[user.pk for user in reviewers]).values_list('pk', flat=True))
        return [user for user in reviewers if user.pk in member_ids and user.is_valid]

    @classmethod
    def get_review_assignees(cls, rules):
        rules = tuple(rules)
        by_org = {}
        for rule in rules:
            reviewers = by_org.setdefault(rule.org_id, {})
            reviewers.update((user.pk, user) for user in rule.reviewers.all())
        assignees = {
            user.pk: user
            for org_id, reviewers in by_org.items()
            for user in cls.filter_available_reviewers(reviewers.values(), org_id)
        }
        if rules and not assignees:
            raise JMSException(
                code='acl_reviewers_unavailable',
                detail=_('No available reviewers. Contact an administrator.'),
            )
        return list(assignees.values())

    # 规则, ip_group, time_period
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))
    review_duration = models.PositiveIntegerField(
        default=0, verbose_name=_('Review exemption duration (hours)'),
        help_text=_('0 means approval is required for every connection.'),
    )

    class Meta(UserAssetAccountBaseACL.Meta):
        verbose_name = _('Login asset acl')
        abstract = False

    def __str__(self):
        return self.name

    def get_review_cache_key(self, user_id, asset_id, account_username):
        account_digest = sha256(account_username.encode('utf-8')).hexdigest()
        return f'asset-review:v1:{self.org_id}:{self.id}:{user_id}:{asset_id}:{account_digest}'

    def is_review_exempt(self, user, asset, account_username):
        if not self.is_active or not self.review_enabled:
            return False
        if not self.review_duration:
            return False
        key = self.get_review_cache_key(user.id, asset.id, account_username)
        try:
            return cache.get(key) is not None
        except Exception:
            logger.exception('Failed to read asset review exemption for ACL %s', self.id)
            return False

    @staticmethod
    def _cache_review(key, ticket_id, timeout):
        try:
            cache.set(key, ticket_id, timeout=timeout)
        except Exception:
            logger.exception('Failed to cache asset review exemption for ticket %s', ticket_id)

    @classmethod
    def cache_approved_review(cls, ticket):
        from tickets.const import TicketState

        reviews = ticket.meta.get('login_asset_reviews') or [ticket.meta.get('login_asset_review')]
        if ticket.state != TicketState.approved:
            return
        connections = ticket.meta.get('login_asset_connections') or [{
            'asset_id': str(ticket.apply_login_asset_id), 'account': ticket.apply_login_account,
            'reviews': reviews,
        }]
        for entry in connections:
            cls.cache_connection_review(ticket, entry)

    @classmethod
    def cache_connection_review(cls, ticket, entry):
        for review in filter(None, entry.get('reviews', [])):
            with tmp_to_org(ticket.org_id):
                acl = cls.objects.filter(id=review.get('acl_id'), is_active=True, review_enabled=True).first()
            if not acl or not acl.review_duration:
                continue
            key = acl.get_review_cache_key(ticket.apply_login_user_id, entry['asset_id'], entry['account'])
            if key != review.get('cache_key'):
                continue
            transaction.on_commit(lambda key=key, timeout=acl.review_duration * 3600: cls._cache_review(key, str(ticket.id), timeout))

    def create_login_asset_review_ticket(self, user, asset, account_username, assignees, org_id, *, review_acls=None, reason='', connections=None):
        from tickets.const import TicketType
        from tickets.models import ApplyLoginAssetTicket
        title = _('Login asset confirm') + ' ({})'.format(user)
        data = {
            'title': title,
            'org_id': org_id,
            'applicant': user,
            'apply_login_user': user,
            'apply_login_asset': asset,
            'apply_login_account': account_username,
            'type': TicketType.login_asset_confirm,
            'comment': reason,
            'meta': {'login_asset_reviews': [
                {'acl_id': str(rule.id),
                 'cache_key': rule.get_review_cache_key(user.id, asset.id, account_username)}
                for rule in (review_acls or (self,))
            ]},
        }
        data['meta']['login_asset_connections'] = [{
            'asset_id': str(asset.pk), 'asset_name': asset.name, 'asset_address': asset.address,
            'account': account_username, 'reason': reason,
            'reviews': data['meta']['login_asset_reviews'],
        }]
        if connections:
            if len(connections) > 1:
                data['title'] += ' ({})'.format(len(connections))
            data['meta']['login_asset_connections'] = [
                {'token_id': str(token.pk), 'asset_id': str(token.asset_id),
                 'asset_name': token.asset.name, 'asset_address': token.asset.address,
                 'account': token.acl_context['username'],
                 'reason': token.acl_context.get('reason', '') or token.comment or '',
                 'reviews': [
                     {'acl_id': str(rule.pk), 'cache_key': rule.get_review_cache_key(
                         user.pk, token.asset_id, token.acl_context['username'],
                     )} for rule in rules
                 ]}
                for token, rules in connections
            ]
        if connections and len(connections) > 1:
            data['comment'] = '\n\n'.join(
                '{}: {} ({})\n{}: {}\n{}: {}'.format(
                    _('Asset'), token.asset.name, token.asset_id,
                    _('Account'), token.acl_context['username'],
                    _('Connection reason'), token.acl_context.get('reason', '') or '-',
                ) for token, connection_rules in connections
            )
        ticket = ApplyLoginAssetTicket.objects.create(**data)
        ticket.open_by_system(assignees)
        return ticket


@dataclass(frozen=True)
class LoginAssetPolicy:
    rules: tuple

    ActionChoices = ActionChoices

    @property
    def decision_rule(self):
        return next((rule for rule in self.rules if rule.action == ActionChoices.reject), self.rules[0])

    @property
    def action(self):
        return self.decision_rule.action

    @property
    def id(self):
        return self.decision_rule.id

    @property
    def name(self):
        return self.decision_rule.name

    def is_action(self, action):
        return self.action == action

    def enabled(self, field):
        return self.action == ActionChoices.accept and any(getattr(rule, field) for rule in self.rules)

    def allows_noninteractive_for(self, user, account, asset=None):
        fields = tuple(field for field in LoginAssetACL.CONTROL_FIELDS if field != 'push_account_enabled')
        if self.action != ActionChoices.accept or any(self.enabled(field) for field in fields):
            return False
        username = account if isinstance(account, str) else getattr(account, 'username', '')
        source = None if isinstance(account, str) else account
        if self.enabled('push_account_enabled') and LoginAssetACL.is_same_account(user, source, username):
            from accounts.provisioning import needs_account_preparation
            if source is None:
                source = asset.all_valid_accounts.filter(username=user.username).first() if asset else None
            return bool(source and not needs_account_preparation(source))
        return True

    def pending_reviews(self, user, asset, username):
        review_rules = tuple(rule for rule in self.rules if rule.review_enabled)
        LoginAssetACL.get_review_assignees(review_rules)
        rules = tuple(rule for rule in review_rules if not rule.is_review_exempt(user, asset, username))
        if rules != review_rules:
            LoginAssetACL.get_review_assignees(rules)
        return rules
