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
        }
        ticket = ApplyLoginAssetTicket.objects.create(**data)
        ticket.open_by_system(assignees, workflow=workflow)
        return ticket
