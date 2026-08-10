from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from users.const import (
    AppletConnectionMethod, ConnectDefaultOpenMethod, FileNameConflictResolution,
    KeyboardLayout, RDPClientOption, RDPColorQuality, RDPResolution, RDPSmartSize,
    Themes,
)


class ListMultipleChoiceField(serializers.MultipleChoiceField):

    def to_representation(self, value):
        return list(value)

    def to_internal_value(self, data):
        return list(super().to_internal_value(data))


class LunaSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Luna default')

    LUNA_DEFAULT_IS_ASYNC_ASSET_TREE = serializers.BooleanField(
        required=False, label=_('Async loading of asset tree')
    )
    LUNA_DEFAULT_CONNECT_DEFAULT_OPEN_METHOD = serializers.ChoiceField(
        choices=ConnectDefaultOpenMethod.choices, required=False,
        label=_('Connect default open method')
    )
    LUNA_DEFAULT_THEMES = serializers.ChoiceField(
        choices=Themes.choices, required=False, label=_('Theme')
    )
    LUNA_DEFAULT_RDP_RESOLUTION = serializers.ChoiceField(
        choices=RDPResolution.choices, required=False, label=_('RDP resolution')
    )
    LUNA_DEFAULT_KEYBOARD_LAYOUT = serializers.ChoiceField(
        choices=KeyboardLayout.choices, required=False, label=_('Keyboard layout')
    )
    LUNA_DEFAULT_RDP_CLIENT_OPTION = ListMultipleChoiceField(
        choices=RDPClientOption.choices, required=False,
        label=_('RDP client option')
    )
    LUNA_DEFAULT_RDP_COLOR_QUALITY = serializers.ChoiceField(
        choices=RDPColorQuality.choices, required=False,
        label=_('RDP color quality')
    )
    LUNA_DEFAULT_RDP_SMART_SIZE = serializers.ChoiceField(
        choices=RDPSmartSize.choices, required=False, label=_('RDP smart size'),
        help_text=_(
            'Determines whether the client computer should scale the content on the remote '
            'computer to fit the window size of the client computer when the window is resized.'
        )
    )
    LUNA_DEFAULT_APPLET_CONNECTION_METHOD = serializers.ChoiceField(
        choices=AppletConnectionMethod.choices, required=False,
        label=_('Remote app connect method')
    )
    LUNA_DEFAULT_FILE_NAME_CONFLICT_RESOLUTION = serializers.ChoiceField(
        choices=FileNameConflictResolution.choices, required=False,
        label=_('File name conflict resolution')
    )
    LUNA_DEFAULT_CHARACTER_TERMINAL_FONT_SIZE = serializers.IntegerField(
        min_value=1, max_value=9999, required=False,
        label=_('Terminal font size')
    )
    LUNA_DEFAULT_IS_BACKSPACE_AS_CTRL_H = serializers.BooleanField(
        required=False, label=_('Backspace as Ctrl+H')
    )
    LUNA_DEFAULT_IS_RIGHT_CLICK_QUICKLY_PASTE = serializers.BooleanField(
        required=False, label=_('Right click quickly paste')
    )
    LUNA_DEFAULT_TERMINAL_THEME_NAME = serializers.CharField(
        max_length=128, required=False, label=_('Terminal theme name')
    )
