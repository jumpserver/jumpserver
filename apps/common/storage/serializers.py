from urllib.parse import urlparse

from django.utils.translation import gettext_lazy as _
from django.db.models import Manager
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from common.serializers import MethodSerializer
from common.serializers.fields import ReadableHiddenField


storage_default_help_text = _(
    'set as the default storage, will make new Component use the current '
    'storage by default, without affecting existing Component'
)


class BaseStorageSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, max_length=128, label=_("Name"))
    storage_type_serializer_classes_mapping = {}
    meta = MethodSerializer()

    class Meta:
        model: Manager | None = None
        fields = ['id', 'name', 'type', 'meta', 'is_default', 'comment']
        extra_kwargs = {
            'is_default': {'help_text': storage_default_help_text},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = self.__class__.Meta.model
        self.fields['name'].validators.append(UniqueValidator(queryset=model.objects.all()))

    def validate_meta(self, meta):
        _meta = self.instance.meta if self.instance else {}
        _meta.update(meta)
        return _meta

    def get_meta_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)

        if isinstance(self.instance, self.__class__.Meta.model):
            _type = self.instance.type
        else:
            _type = self.context['request'].query_params.get('type')

        type_serializer = self.storage_type_serializer_classes_mapping.get(_type)
        serializer_class = type_serializer or default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class
        return serializer

    def to_representation(self, instance):
        data = super().to_representation(instance)
        need_translate_comments = {
            'Store locally': _('Store locally'),
            'Do not save': _('Do not save')
        }
        comment = instance.comment
        data['comment'] = need_translate_comments.get(comment, comment)
        return data


def es_host_format_validator(host):
    if '#' in host:
        raise serializers.ValidationError(_('The address cannot contain the special character `#`'))
    h = urlparse(host)
    default_error_msg = _('The address format is incorrect')
    if h.scheme not in ['http', 'https']:
        raise serializers.ValidationError(default_error_msg)
    if ':' not in h.netloc:
        raise serializers.ValidationError(default_error_msg)
    _host, _port = h.netloc.rsplit(':', maxsplit=1)
    if not _host:
        error_msg = _('Host invalid')
        raise serializers.ValidationError(error_msg)
    if not _port.isdigit():
        error_msg = _('Port invalid')
        raise serializers.ValidationError(error_msg)
    return host


class StorageTypeESSerializer(serializers.Serializer):
    HOSTS = serializers.ListField(
        child=serializers.CharField(validators=[es_host_format_validator]),
        label=_('Hosts'), help_text=_(
            'If there are multiple hosts, use a comma (,) to separate them. <br>'
            '(For example: http://www.jumpserver.a.com:9100, http://www.jumpserver.b.com:9100)'),
        allow_null=True
    )
    INDEX_BY_DATE = serializers.BooleanField(
        default=False, label=_('Index by date'),
        help_text=_('Whether to create an index by date')
    )
    INDEX = serializers.CharField(
        max_length=1024, default='jumpserver', label=_('Index'), allow_null=True
    )
    DOC_TYPE = ReadableHiddenField(default='_doc', label=_('Doc type'), allow_null=True)
    IGNORE_VERIFY_CERTS = serializers.BooleanField(
        default=False, label=_('Ignore Certificate Verification'),
        source='OTHER.IGNORE_VERIFY_CERTS', allow_null=True,
    )
