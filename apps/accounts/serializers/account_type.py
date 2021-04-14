from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import AccountType
from ..const import FieldDefinitionTypeChoices


__all__ = ['AccountTypeSerializer']


class FieldDefinitionSerializer(serializers.Serializer):
    name = serializers.SlugField(max_length=128, required=True, label=_('Name'))
    type = serializers.ChoiceField(
        choices=FieldDefinitionTypeChoices.choices, default=FieldDefinitionTypeChoices.str,
        label=_('Type')
    )
    required = serializers.BooleanField(default=False, label=_('Required'))
    read_only = serializers.BooleanField(default=False, label=_('Read only'))
    write_only = serializers.BooleanField(default=False, label=_('Write only'))
    default = serializers.CharField(max_length=256, required=False, label=_('Default'))
    label = serializers.CharField(max_length=256, required=True, label=_('Label'))
    help_text = serializers.CharField(max_length=2048, required=False, label=_('Help text'))


class AccountTypeSerializer(serializers.ModelSerializer):
    protocol_choices = (
        ('ssh', 'SSH'), ('rdp', 'RDP'), ('telnet', 'Telnet'), ('vnc', 'VNC'),
        ('http', 'HTTP'), ('https', 'HTTPS'),
        ('mysql', 'MySQL'), ('oracle', 'Oracle'),
        ('mariadb', 'MariaDB'), ('postgresql', 'PostgreSQL'),
        ('other', 'Other')
    )

    protocol = serializers.ChoiceField(required=True, choices=protocol_choices, label=_('Protocol'))
    fields_definition = serializers.ListField(
        child=FieldDefinitionSerializer(), required=False, label=_('Fields Definition')
    )

    class Meta:
        model = AccountType
        fields = [
            'id', 'name', 'category', 'protocol', 'secret_type', 'fields_definition', 'is_builtin',
            'comment', 'created_by', 'date_created', 'date_updated',
        ]
