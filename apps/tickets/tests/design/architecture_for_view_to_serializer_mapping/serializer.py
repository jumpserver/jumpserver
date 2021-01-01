import data_tree
from rest_framework import serializers


class TreeSerializerMetaClass(serializers.SerializerMetaclass, type):

    @classmethod
    def get_data_tree(mcs, field):
        data_dict_to_tree = getattr(field, 'data_dict_to_tree', None)
        if not callable(data_dict_to_tree):
            return
        tree = data_dict_to_tree()
        return tree

    @classmethod
    def get_json_fields_serializer(mcs, bases, attrs):
        fields_serializer = {}
        json_fields_mapping = attrs.get('json_fields_mapping')
        if not isinstance(json_fields_mapping, dict):
            return fields_serializer

        declared_fields = mcs._get_declared_fields(bases, attrs)

        for field_name, serializer_path_list in json_fields_mapping.items():
            if field_name not in declared_fields:
                continue
            field = declared_fields[field_name]
            if not isinstance(field, TreeSerializer):
                continue
            field_tree = mcs.get_data_tree(field)
            if field_tree is None:
                continue

            serializer_path = '.'.join(serializer_path_list)
            field_serializer = field_tree.get(serializer_path)
            if not field_serializer:
                continue
            fields_serializer[field_name] = field_serializer()

        return fields_serializer

    def __new__(mcs, name, bases, attrs):
        tree = mcs.get_data_tree(bases)
        attrs['data_tree'] = tree
        json_fields_serializer = mcs.get_json_fields_serializer(bases, attrs)
        attrs.update(json_fields_serializer)
        return super().__new__(mcs, name, bases, attrs)


class TreeSerializer(serializers.Serializer):
    data_dict = {}

    @classmethod
    def data_dict_to_tree(cls):
        tree = data_tree.Data_tree_node(arg_data=cls.data_dict)
        return tree


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


class MetaSerializer(TreeSerializer):
    data_dict = {
        'type': {
            'apply_asset': {
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
    meta = MetaSerializer()
    meta2 = MetaSerializer()

