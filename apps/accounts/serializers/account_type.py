from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import AccountType
from ..const import PropertyTypeChoices


__all__ = ['AccountTypeSerializer']


class PropertiesSerializer(serializers.Serializer):
    name = serializers.SlugField(max_length=128, required=True, label=_('Name'))
    type = serializers.ChoiceField(
        choices=PropertyTypeChoices.choices, default=PropertyTypeChoices.str,
        label=_('Type')
    )
    required = serializers.BooleanField(default=False, label=_('Required'))
    read_only = serializers.BooleanField(default=False, label=_('Read only'))
    write_only = serializers.BooleanField(default=False, label=_('Write only'))
    default = serializers.CharField(max_length=256, required=False, label=_('Default'))
    label = serializers.CharField(max_length=256, required=True, label=_('Label'))
    help_text = serializers.CharField(max_length=2048, required=False, label=_('Help text'))


class AccountTypeSerializer(serializers.ModelSerializer):
    class ProtocolChoices(TextChoices):
        ssh = 'ssh', 'SSH'
        rdp = 'rdp', 'RDP'
        telnet = 'telnet', 'Telnet'
        vnc = 'vnc', 'VNC'
        http = 'http', 'HTTP'
        https = 'https', 'HTTPS'
        mysql = 'mysql', 'MySQL'
        oracle = 'oracle', 'Oracle'
        mariadb = 'mariadb', 'MariaDB'
        postgresql = 'postgresql', 'PostgreSQL'
        other = 'other', 'Other'

    protocol = serializers.ChoiceField(
        required=True, choices=ProtocolChoices.choices, label=_('Protocol')
    )
    category_display = serializers.ReadOnlyField(
        source='get_category_display', label=_('Category display')
    )
    secret_type_display = serializers.ReadOnlyField(
        source='get_secret_type_display', label=_('Secret type display')
    )
    protocol_display = serializers.SerializerMethodField()
    properties = serializers.ListField(
        child=PropertiesSerializer(), required=False, label=_('Properties')
    )

    class Meta:
        model = AccountType
        fields = [
            'id', 'name', 'category', 'category_display', 'protocol', 'protocol_display',
            'secret_type', 'secret_type_display', 'properties', 'is_builtin',
            'comment', 'created_by', 'date_created', 'date_updated',
        ]
        extra_kwargs = {
            'category': {'default': AccountType.CategoryChoices.os}
        }

    def get_protocol_display(self, obj):
        return getattr(self.__class__.ProtocolChoices, obj.protocol).label
