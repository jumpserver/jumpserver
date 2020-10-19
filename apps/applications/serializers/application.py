# coding: utf-8
#

from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .. import models

__all__ = [
    'ApplicationSerializer',
]


class ApplicationSerializer(BulkOrgResourceModelSerializer):

    class Meta:
        model = models.Application
        fields = [
            'id', 'name', 'category', 'type', 'get_type_display', 'attrs',
            'created_by', 'date_created', 'date_updated', 'comment'
        ]
        read_only_fields = [
            'created_by', 'date_created', 'date_updated', 'get_type_display',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app_type = ''
        attrs_data = {}
        if self.instance:
            app_type = self.instance.type
            attrs_data = self.instance.attrs
        request = self.context.get('request')
        if request:
            app_type = request.query_params.get('type')
        if hasattr(self, 'initial_data'):
            app_type = self.initial_data.get('type')
            attrs_data = self.initial_data.get('attrs')
        if not app_type:
            return
        attrs_cls = models.Category.get_type_serializer_cls(app_type)
        if attrs_data:
            attrs_serializer = attrs_cls(data=attrs_data)
        else:
            attrs_serializer = attrs_cls()
        self.fields['attrs'] = attrs_serializer

