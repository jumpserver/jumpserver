from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import ugettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}'


class TicketType(TextChoices):
    general = 'general', _("General")
    login_confirm = 'login_confirm', _("Login confirm")
    apply_asset = 'apply_asset', _('Apply for asset')
    apply_application = 'apply_application', _('Apply for application')
    login_asset_confirm = 'login_asset_confirm', _('Login asset confirm')
    command_confirm = 'command_confirm', _('Command confirm')


class TicketState(TextChoices):
    open = 'open', _('Open')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')
    closed = 'closed', _('Closed')


class ProcessStatus(TextChoices):
    notified = 'notified', _('Notified')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')


class TicketStatus(TextChoices):
    open = 'open', _("Open")
    closed = 'closed', _("Closed")


class TicketAction(TextChoices):
    open = 'open', _("Open")
    close = 'close', _("Close")
    approve = 'approve', _('Approve')
    reject = 'reject', _('Reject')


class TicketApprovalLevel(IntegerChoices):
    one = 1, _("One level")
    two = 2, _("Two level")


class TicketApprovalStrategy(TextChoices):
    super = 'super', _("Super user")
    admin = 'admin', _("Admin user")
    super_admin = 'super_admin', _("Super admin user")
    custom = 'custom', _("Custom user")
