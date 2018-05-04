# -*- coding: utf-8 -*-
#
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


alphanumeric = RegexValidator(r'^[0-9a-zA-Z_@\-\.]*$', _('Special char not allowed'))