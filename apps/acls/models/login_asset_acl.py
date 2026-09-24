from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from .base import UserAssetAccountBaseACL


class LoginAssetACL(UserAssetAccountBaseACL):
    workflow = models.ForeignKey(
        'tickets.Workflow', null=True, blank=True, on_delete=models.PROTECT,
        related_name='+', verbose_name=_('Workflow'),
    )
    # 规则, ip_group, time_period
    rules = models.JSONField(default=dict, verbose_name=_('Rule'))

    class Meta(UserAssetAccountBaseACL.Meta):
        verbose_name = _('Login asset acl')
        abstract = False

    def __str__(self):
        return self.name

    @classmethod
    @transaction.atomic
    def create_login_asset_review_ticket(cls, user, asset, account_username, assignees, org_id, workflow=None):
        from tickets.const import TicketType
        from tickets.models import Ticket
        title = _('Login asset confirm') + ' ({})'.format(user)
        data = {
            'title': title,
            'org_id': org_id,
            'applicant': user,
            'type': TicketType.login_asset_confirm,
            'request_data': {
                'apply_login_user': str(user.pk),
                'apply_login_asset': str(asset.pk),
                'apply_login_account': account_username,
            },
        }
        ticket = Ticket.objects.create(**data)
        ticket.open_by_system(assignees, workflow=workflow)
        return ticket
