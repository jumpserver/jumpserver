import json

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from users.const import (
    RDPResolution, RDPSmartSize, KeyboardLayout,
    RDPClientOption, AppletConnectionMethod, RDPColorQuality,
)


class MultipleChoiceField(serializers.MultipleChoiceField):

    def to_representation(self, keys):
        if isinstance(keys, str):
            keys = json.loads(keys)
        return keys

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return json.dumps(list(data))


class BasicSerializer(serializers.Serializer):
    is_async_asset_tree = serializers.BooleanField(
        required=False, default=True, label=_('Async loading of asset tree')
    )


class GraphicsSerializer(serializers.Serializer):
    rdp_resolution = serializers.ChoiceField(
        RDPResolution.choices, default=RDPResolution.AUTO,
        required=False, label=_('RDP resolution')
    )
    keyboard_layout = serializers.ChoiceField(
        KeyboardLayout.choices, default=KeyboardLayout.EN_US_QWERTY,
        required=False, label=_('Keyboard layout')
    )
    rdp_client_option = MultipleChoiceField(
        choices=RDPClientOption.choices, default={RDPClientOption.FULL_SCREEN},
        label=_('RDP client option'), required=False
    )
    rdp_color_quality = serializers.ChoiceField(
        choices=RDPColorQuality.choices, default=RDPColorQuality.HIGH,
        label=_('RDP color quality'), required=False
    )
    rdp_smart_size = serializers.ChoiceField(
        RDPSmartSize.choices, default=RDPSmartSize.DISABLE,
        required=False, label=_('Rdp smart size'),
        help_text=_('Determines whether the client computer should scale the content on the remote '
                    'computer to fit the window size of the client computer when the window is resized.')
    )
    applet_connection_method = serializers.ChoiceField(
        AppletConnectionMethod.choices, default=AppletConnectionMethod.WEB,
        required=False, label=_('Remote application connection method')
    )


class CommandLineSerializer(serializers.Serializer):
    character_terminal_font_size = serializers.IntegerField(
        default=14, min_value=1, max_value=9999, required=False,
        label=_('Character terminal font size'),
    )
    is_backspace_as_ctrl_h = serializers.BooleanField(
        required=False, default=False, label=_('Backspace as Ctrl+H')
    )
    is_right_click_quickly_paste = serializers.BooleanField(
        required=False, default=False, label=_('Right click quickly paste')
    )


class LunaSerializer(serializers.Serializer):
    basic = BasicSerializer(required=False, label=_('Basic'))
    graphics = GraphicsSerializer(required=False, label=_('Graphics'))
    command_line = CommandLineSerializer(required=False, label=_('Command line'))
