from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}'


class TicketTypeChoices(TextChoices):
    general = 'general', _("General")
    login_confirm = 'login_confirm', _("Login confirm")
    apply_asset = 'apply_asset', _('Apply for asset')
    apply_application = 'apply_application', _('Apply for application')


class TicketActionChoices(TextChoices):
    open = 'open', _('Open')
    approve = 'approve', _('Approve')
    reject = 'reject', _('Reject')
    close = 'close', _('Close')


class TicketStatusChoices(TextChoices):
    open = 'open', _("Open")
    closed = 'closed', _("Closed")
