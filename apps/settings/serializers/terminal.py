from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class TerminalSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Terminal')

    SORT_BY_CHOICES = (
        ('name', _('Name')),
        ('ip', _('Address'))
    )

    PAGE_SIZE_CHOICES = (
        ('all', _('All')),
        ('auto', _('Auto')),
        ('10', '10'),
        ('15', '15'),
        ('25', '25'),
        ('50', '50'),
    )
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.ChoiceField(
        choices=[
            ('auto', _('Auto(Enabled for the first 5 minutes after startup, then disabled.)')),
            (True, _('Enable')), (False, _('Disable'))
        ],
        required=True, label=_('Registration'),
        help_text=_(
            "Allow component register, after all component setup, you should disable this for security"
        )
    )
    TERMINAL_PASSWORD_AUTH = serializers.BooleanField(
        required=False, label=_("Password"),
        help_text=_(
            '* Allow users to log in to the KoKo component via password authentication'
        )
    )
    TERMINAL_PUBLIC_KEY_AUTH = serializers.BooleanField(
        required=False, label=_("Public key"),
        help_text=_(
            '* Allow users to log in to the KoKo component via Public key authentication'
            '<br/>'
            'If third-party authentication services, such as DS/LDAP, are enabled, you should '
            'disable this option to prevent users from logging in after being deleted from the DS/LDAP server'
        )
    )
    TERMINAL_ASSET_LIST_SORT_BY = serializers.ChoiceField(
        SORT_BY_CHOICES, required=False, label=_('Asset sorting')
    )
    TERMINAL_ASSET_LIST_PAGE_SIZE = serializers.ChoiceField(
        PAGE_SIZE_CHOICES, required=False, label=_('Asset page size')
    )
    TERMINAL_MAGNUS_ENABLED = serializers.BooleanField(
        label="Magnus",
        help_text=_(
            '* You can individually configure the service address and port in the service endpoint'
            '<br/>'
            'If enabled, the Luna page will display the DB client launch method when connecting to assets'
        )
    )
    TERMINAL_RAZOR_ENABLED = serializers.BooleanField(
        label="Razor",
        help_text=_(
            '* You can individually configure the service address and port in the service endpoint'
            '<br/>'
            'If enabled, the Luna page will display the download rdp file button '
            'and RDP Client launch method when connecting to assets'
        )
    )
    TERMINAL_KOKO_SSH_ENABLED = serializers.BooleanField(
        label=_("Client connection"),
        help_text=_(
            '* Allow connecting to the KoKo component via SSH client'
            '<br/>'
            'If enabled, the Luna page will display the SSH client launch method when connecting to assets'
        )
    )
