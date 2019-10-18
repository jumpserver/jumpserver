# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _


GENERAL_LIMIT_SPECIAL_CHARACTERS_HELP_TEXT = _(
    'Only Numbers、letters、 chinese and characters ( {} ) are allowed'
).format(" ".join(['.', '_', '@', '-']))

GENERAL_LIMIT_SPECIAL_CHARACTERS_PATTERN = r"^[\._@\w-]+$"

GENERAL_LIMIT_SPECIAL_CHARACTERS_ERROR_MSG = \
    _("* The contains characters that are not allowed")
