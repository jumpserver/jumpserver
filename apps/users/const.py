# -*- coding: utf-8 -*-
#
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

TICKET_DETAIL_URL = '/ui/#/tickets/tickets/{id}'


class SystemOrOrgRole(TextChoices):
    SYSTEM_ADMIN = 'system_admin', _('System administrator')
    SYSTEM_AUDITOR = 'system_auditor', _('System auditor')
    ORG_ADMIN = 'org_admin', _('Organization administrator')
    ORG_AUDITOR = 'org_auditor', _("Organization auditor")
    USER = 'user', _('User')


class PasswordStrategy(TextChoices):
    email = 'email', _('Reset link will be generated and sent to the user')
    custom = 'custom', _('Set password')


class RDPResolution(TextChoices):
    AUTO = 'auto', _('AUTO')
    RES_1024x768 = '1024x768', '1024x768'
    RES_1366x768 = '1366x768', '1366x768'
    RES_1600x900 = '1600x900', '1600x900'
    RES_1920x1080 = '1920x1080', '1920x1080'


class RDPClientOption(TextChoices):
    FULL_SCREEN = 'full_screen', _('Full screen')
    MULTI_SCREEN = 'multi_screen', _('Multi screen')
    DRIVES_REDIRECT = 'drives_redirect', _('Drives redirect')


class ConnectDefaultOpenMethod(TextChoices):
    CURRENT = 'current', _('Current window')
    NEW = 'new', _('New window')


class RDPSmartSize(TextChoices):
    DISABLE = '0', _('Disable')
    ENABLE = '1', _('Enable')


class RDPColorQuality(TextChoices):
    HIGH = '32', _('High（32 bit）')
    MEDIUM = '16', _('Medium（16 bit）')


class KeyboardLayout(TextChoices):
    EN_US_QWERTY = 'en-us-qwerty', 'US English (Qwerty)'
    EN_UK_QWERTY = 'en-gb-qwerty', 'UK English (Qwerty)'
    JA_JP_QWERTY = 'ja-jp-qwerty', 'Japanese (Qwerty)'
    FR_FR_AZERTY = 'fr-fr-azerty', 'French (Azerty)'
    FR_CH_QWERTZ = 'fr-ch-qwertz', 'Swiss French (Qwertz)'
    FR_BE_AZERTY = 'fr-be-azerty', 'Belgian French (Azerty)'
    TR_TR_QWERTY = 'tr-tr-qwerty', 'Turkish-Q (Qwerty)'
    ES_ES_QWERTY = 'es-es-qwerty', 'Spanish'
    ES_LATAM_QWERTY = 'es-latam-qwerty', 'Spanish (Latin American)'


class AppletConnectionMethod(TextChoices):
    WEB = 'web', _('Web')
    CLIENT = 'client', _('Client')


class FileNameConflictResolution(TextChoices):
    REPLACE = 'replace', _('Replace')
    SUFFIX = 'suffix', _('Suffix')
