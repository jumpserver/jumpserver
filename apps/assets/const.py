# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _


GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_HELP_TEXT = _(
    'Cannot contain special characters: [ {} ]'
).format(" ".join(['/', '\\']))

GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_PATTERN = r"[/\\]"

GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_ERROR_MSG = \
    _("* The contains characters that are not allowed")
