"""
说明:
    View 获取 serializer_class 的架构设计

问题:
    View 所需的 Serializer Class 中有一个字段，字段的类型并不固定，
    而是由 View 的行为 (比如 type, action) 来决定的.
    使用 View 默认的 get_serializer_class 方法不能实现，因为序列类在被定义的时候，其字段及类型已经固定，
    所以需要一种机制来动态修改序列类中的字段及其类型，即，MetaClass 元类


    例如:
        class MetaASerializer(serializers.Serializer):
            name = serializers.CharField(label='Name')


        class MetaBSerializer(serializers.Serializer):
            age = serializers.IntegerField(label='Age')


        class Serializer(serializers.Serializer):
            meta = serializers.JSONField()

        当 view 获取 serializer 时，无论 action 是什么, 获取到的 Serializer.meta 字段始终是
        serializers.JSONField() 类型

        但我们希望:
            当 view.action = A 时，获取到的 Serializer.meta 是 MetaASerializerMetaASerializer()
            当 view.action = B 时，获取到的 Serializer.meta 是 MetaBSerializerMetaASerializer()

分析:
    问题关键在于数据映射规则的定义和匹配,
    即， 用 View 给定的规则动态去匹配 Serializer Class 中定义的规则, 从而创建出想要的序列类

    当然, 使用 dict 可以很好的解决规则定义问题，但要直接进行匹配, 操作起来比较复杂
    所以, 决定使用以下方案实现, 即, dict, dict-> tree 数据类型转化, tree 搜索:
        Serializer Class 中规则的定义使用 dict,
        View 中指定的规则也使用 dict,
        MetaClass 中进行规则匹配的过程使用 dict tree, 即将给定的 dic 转换为 tree 的数据结构，再进行匹配,
        * dict -> tree 的转化使用 `data-tree` 库来实现


方案:
    view:
        使用元类 MetaClass: 在 View 中动态创建所需要的 Serializer Class

    serializer:
        实现 DynamicMappingField: 序列类的动态映射字段, 用来定义字段的映射规则

        实现 IncludeDynamicMappingFieldSerializerMetaClass:
            在 View 中用来动态创建 Serializer Class.
            即, 用 View 中给定的规则，去匹配 Serializer Class 里每一个 DynamicMappingField 字段定义的规则,
            基于 bases, 创建并返回新的 Serializer Class

        实现 IncludeDynamicMappingFieldSerializerViewMixin:
            实现动态创建 Serializer Class 的逻辑,
            同时定义获取 Serializer Class 中所有 DynamicMappingField 字段匹配规则的方法
            =>
            def get_dynamic_mapping_fields_mapping_rule(self):
                return {
                    'dynamic_mapping_field_name1': `mapping_path`,
                    'dynamic_mapping_field_name2': `mapping_path',
                }
            供 View 子类重写

实现:
    请看 ./serializer.py 和 ./serializer.py

"""
