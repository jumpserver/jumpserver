from django.conf import settings
from django.db.models import TextChoices, IntegerChoices
from django.utils.translation import gettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}?type={type}'


class TicketType(TextChoices):
    general = 'general', _("General")
    apply_asset = 'apply_asset', _('Apply for asset')
    login_confirm = 'login_confirm', _("Login confirm")
    command_confirm = 'command_confirm', _('Command confirm')
    login_asset_confirm = 'login_asset_confirm', _('Login asset confirm')


class TicketState(TextChoices):
    pending = 'pending', _('Open')
    closed = 'closed', _("Cancel")
    reopen = 'reopen', _("Reopen")
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')


class TicketStatus(TextChoices):
    open = 'open', _("Open")
    closed = 'closed', _("Finished")


class StepState(TextChoices):
    pending = 'pending', _('Pending')
    closed = 'closed', _("Closed")
    reopen = 'reopen', _("Reopen")
    approved = 'approved', _('Approved')
    rejected = 'rejected', _('Rejected')


class StepStatus(TextChoices):
    active = 'active', _('Active')
    closed = 'closed', _("Closed")
    pending = 'pending', _('Pending')


class TicketAction(TextChoices):
    open = 'open', _("Open")
    close = 'close', _("Close")
    reject = 'reject', _('Reject')
    approve = 'approve', _('Approve')


class TicketLevel(IntegerChoices):
    one = 1, _("One level")
    two = 2, _("Two level")


class TicketApprovalStrategy(TextChoices):
    org_admin = 'org_admin', _("Org admin")
    custom_user = 'custom_user', _("Custom user")
    super_admin = 'super_admin', _("Super admin")
    super_org_admin = 'super_org_admin', _("Super admin and org admin")


class TicketApplyAssetScope(TextChoices):
    all = 'all', _("All assets")
    permed = 'permed', _("Permed assets")
    permed_valid = 'permed_valid', _('Permed valid assets')

    @classmethod
    def get_scope(cls):
        return settings.TICKET_APPLY_ASSET_SCOPE.lower()

    @classmethod
    def is_permed(cls):
        return cls.get_scope() == cls.permed

    @classmethod
    def is_permed_valid(cls):
        return cls.get_scope() == cls.permed_valid
