import data_tree
from rest_framework import serializers


class IncludeDynamicMappingFieldSerializerMetaClass(serializers.SerializerMetaclass, type):

    @classmethod
    def get_dynamic_mapping_fields(mcs, bases, attrs):
        fields = {}

        fields_mapping_rules = attrs.get('dynamic_mapping_fields_mapping_rule')

        assert isinstance(fields_mapping_rules, dict), (
            '`dynamic_mapping_fields_mapping_rule` type must be `dict`, get `{}`'
            ''.format(type(fields_mapping_rules))
        )

        declared_fields = mcs._get_declared_fields(bases, attrs)

        for field_name, field_mapping_rule in fields_mapping_rules.items():

            assert isinstance(field_mapping_rule, list), (
                '`field_mapping_rule`- can be either a list of keys.'
                'eg. `["type", "apply_asset", "get"]` '
                'but, get type is `{}`, {}'
                ''.format(type(field_mapping_rule), field_mapping_rule)
            )

            if field_name not in declared_fields.keys():
                continue

            declared_field = declared_fields[field_name]
            if not isinstance(declared_field, DynamicMappingField):
                continue

            dynamic_field = declared_field
            mapping_tree = dynamic_field.mapping_tree.copy()

            field = mapping_tree.get(arg_path=field_mapping_rule)

            if not field:
                default_mapping_rule = field_mapping_rule[:-1] + ['default']
                field = mapping_tree.get(arg_path=default_mapping_rule)

            if field is None:
                continue

            if isinstance(field, type):
                field = field()

            fields[field_name] = field

        return fields

    def __new__(mcs, name, bases, attrs):
        dynamic_mapping_fields = mcs.get_dynamic_mapping_fields(bases, attrs)
        attrs.update(dynamic_mapping_fields)
        return super().__new__(mcs, name, bases, attrs)


class DynamicMappingField(serializers.Serializer):
    default_mapping_rules = {}

    def build_mapping_tree(self):
        tree = data_tree.Data_tree_node(arg_data=self.mapping_rules)
        return tree

    def __init__(self, mapping_rules=None, *args, **kwargs):
        self.mapping_rules = mapping_rules or self.default_mapping_rules
        self.mapping_tree = self.build_mapping_tree()
        super().__init__(*args, **kwargs)



# ---


# ticket type
class ApplyAssetSerializer(serializers.Serializer):
    apply_asset = serializers.CharField(label='Apply Asset')


class ApproveAssetSerializer(serializers.Serializer):
    approve_asset = serializers.CharField(label='Approve Asset')


class ApplyApplicationSerializer(serializers.Serializer):
    apply_application = serializers.CharField(label='Application')


class LoginConfirmSerializer(serializers.Serializer):
    login_ip = serializers.IPAddressField()


class LoginTimesSerializer(serializers.Serializer):
    login_times = serializers.IntegerField()


# ticket category
class ApplySerializer(serializers.Serializer):
    apply_datetime = serializers.DateTimeField()


class LoginSerializer(serializers.Serializer):
    login_datetime = serializers.DateTimeField()


meta_mapping_rules = {
    'type': {
        'apply_asset': {
            'default': serializers.CharField(label='default'),
            'get': ApplyAssetSerializer,
            'post': ApproveAssetSerializer,
        },
        'apply_application': ApplyApplicationSerializer,
        'login_confirm': LoginConfirmSerializer,
        'login_times': LoginTimesSerializer
    },
    'category': {
        'apply': ApplySerializer,
        'login': LoginSerializer
    }
}


class TicketSerializer(serializers.Serializer):
    title = serializers.CharField(label='Title')
    type = serializers.ChoiceField(choices=('apply_asset', 'apply_application'), label='Type')
    meta1 = DynamicMappingField(mapping_rules=meta_mapping_rules)
    meta2 = DynamicMappingField(mapping_rules=meta_mapping_rules)

