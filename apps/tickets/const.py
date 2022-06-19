from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import ugettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}?type={type}'


class TicketType(TextChoices):
    general = 'general', _("General")
    login_confirm = 'login_confirm', _("Login confirm")
    apply_asset = 'apply_asset', _('Apply for asset')
    apply_application = 'apply_application', _('Apply for application')
    login_asset_confirm = 'login_asset_confirm', _('Login asset confirm')
    command_confirm = 'command_confirm', _('Command confirm')


class TicketState(TextChoices):
    pending = 'pending', _('Open')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')
    closed = 'closed', _("Cancel")
    reopen = 'reopen', _("Reopen")


class TicketStatus(TextChoices):
    open = 'open', _("Open")
    closed = 'closed', _("Finished")


class StepState(TextChoices):
    pending = 'pending', _('Pending')
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')
    closed = 'closed', _("Closed")
    reopen = 'reopen', _("Reopen")


class StepStatus(TextChoices):
    pending = 'pending', _('Pending')
    active = 'active', _('Active')
    closed = 'closed', _("Closed")


class TicketAction(TextChoices):
    open = 'open', _("Open")
    close = 'close', _("Close")
    approve = 'approve', _('Approve')
    reject = 'reject', _('Reject')


class TicketLevel(IntegerChoices):
    one = 1, _("One level")
    two = 2, _("Two level")


class TicketApprovalStrategy(TextChoices):
    super_admin = 'super_admin', _("Super admin")
    org_admin = 'org_admin', _("Org admin")
    super_org_admin = 'super_org_admin', _("Super admin and org admin")
    custom_user = 'custom_user', _("Custom user")
