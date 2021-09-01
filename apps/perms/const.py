# -*- coding: utf-8 -*-
#
from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class AuthorizationRules(TextChoices):
    manual = 'manual', _('Manual authorization')
    ticket = 'ticket', _('Ticket authorization')
