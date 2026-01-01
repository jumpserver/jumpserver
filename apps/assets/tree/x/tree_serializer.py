from rest_framework import serializers


class AssetDataSerializer(serializers.Serializer):
    platform_type = serializers.CharField()
    org_name = serializers.CharField()
    sftp = serializers.CharField()
    platform = serializers.CharField()
    name = serializers.CharField()


class NodeDataSerializer(serializers.Serializer):
    id = serializers.CharField()
    key = serializers.CharField()
    value = serializers.CharField()
    assets_amount = serializers.IntegerField()
    assets_amount_total = serializers.IntegerField()
    children_count_total = serializers.IntegerField()


META_DATA_SERIALIZER_MAP = {
    'node': NodeDataSerializer,
    'asset': AssetDataSerializer,
}


class TreeNodeMetaSerializer(serializers.Serializer):
    type = serializers.CharField()
    data = serializers.SerializerMethodField()

    def get_data(self, obj):
        # 同时支持 dict / object
        meta_type = getattr(obj, 'type', None)
        raw_data = getattr(obj, 'data', None)

        serializer_cls = META_DATA_SERIALIZER_MAP.get(meta_type)
        if not serializer_cls:
            return raw_data

        return serializer_cls(raw_data).data


class TreeNodeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    title = serializers.CharField()
    pId = serializers.CharField()
    isParent = serializers.BooleanField()
    open = serializers.BooleanField()
    meta = TreeNodeMetaSerializer()


# Example usage:
tree_nodes = []
serializer = TreeNodeSerializer(tree_nodes, many=True)