from hashlib import sha256

from django.core.cache import cache
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from orgs.utils import tmp_to_org
from .base import UserAssetAccountBaseACL

logger = get_logger(__name__)


class LoginAssetACL(UserAssetAccountBaseACL):
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
        if not self.is_active or not self.is_action(self.ActionChoices.review):
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

        review = ticket.meta.get('login_asset_review')
        if ticket.state != TicketState.approved or not review:
            return
        with tmp_to_org(ticket.org_id):
            acl = cls.objects.filter(
                id=review.get('acl_id'), is_active=True, action=cls.ActionChoices.review,
            ).first()
        if not acl or not acl.review_duration:
            return
        key = acl.get_review_cache_key(
            ticket.apply_login_user_id, ticket.apply_login_asset_id, ticket.apply_login_account,
        )
        if key != review.get('cache_key'):
            return
        ticket_id = str(ticket.id)
        timeout = acl.review_duration * 3600
        transaction.on_commit(lambda: cls._cache_review(key, ticket_id, timeout))

    def create_login_asset_review_ticket(self, user, asset, account_username, assignees, org_id):
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
            'meta': {'login_asset_review': {
                'acl_id': str(self.id),
                'cache_key': self.get_review_cache_key(user.id, asset.id, account_username),
            }},
        }
        ticket = ApplyLoginAssetTicket.objects.create(**data)
        ticket.open_by_system(assignees)
        return ticket
