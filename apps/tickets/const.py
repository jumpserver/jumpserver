from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import ugettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}'


class TicketTypeChoices(TextChoices):
    general = 'general', _("General")
    login_confirm = 'login_confirm', _("Login confirm")
    apply_asset = 'apply_asset', _('Apply for asset')
    apply_application = 'apply_application', _('Apply for application')
    login_asset_confirm = 'login_asset_confirm', _('Login asset confirm')
    command_confirm = 'command_confirm', _('Command confirm')


class TicketActionChoices(TextChoices):
    open = 'open', _('Open')
    approve = 'approve', _('Approve')
    reject = 'reject', _('Reject')
    close = 'close', _('Close')


class TicketStatusChoices(TextChoices):
    open = 'open', _("Open")
    closed = 'closed', _("Closed")


class TicketApproveLevelChoices(IntegerChoices):
    one = 1, _("One level")
    two = 2, _("Two level")


class TicketApproveStrategyChoices(TextChoices):
    super = 'super', _("Super user")
    system = 'super_admin', _("Super admin user")
    all = 'all_user', _("All user")
