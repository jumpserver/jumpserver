from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class TicketTypeChoices(TextChoices):
    general = 'general', _("General")
    login_confirm = 'login_confirm', _("Login confirm")
    apply_asset = 'apply_asset', _('Apply for asset')
    apply_application = 'apply_application', _('Apply for application')

    @classmethod
    def types(cls):
        return set(dict(cls.choices).keys())


class TicketActionChoices(TextChoices):
    approve = 'approve', _('Approve')
    reject = 'reject', _('Reject')


class TicketStatusChoices(TextChoices):
    open = 'open', _("Open")
    closed = 'closed', _("Closed")