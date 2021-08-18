# -*- coding: utf-8 -*-
#
from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}'


class SystemOrOrgRole(TextChoices):
    SYSTEM_ADMIN = 'system_Admin', _('System administrator')
    SYSTEM_AUDITOR = 'system_Auditor', _('System auditor')
    ORG_ADMIN = 'org_Admin', _('Organization administrator')
    ORG_AUDITOR = 'org_Auditor', _("Organization auditor")
    USER = 'User', _('User')


class PasswordStrategy(TextChoices):
    email = 'email', _('Reset link will be generated and sent to the user')
    custom = 'custom', _('Set password')
