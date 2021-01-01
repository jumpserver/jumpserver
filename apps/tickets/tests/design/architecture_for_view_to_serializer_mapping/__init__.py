"""
说明:
    View 获取 serializer_class 的架构设计

问题:
    View 所需的 Serializer 中有一个 JSONField 字段，而字段的值并不固定，是由 View 的行为 (比如action) 而决定的.
    使用 View 默认的 get_serializer_class 方法不能解决


    例如:
        class MetaASerializer(serializers.Serializer):
            name = serializers.CharField(label='Name')


        class MetaBSerializer(serializers.Serializer):
            age = serializers.IntegerField(label='Age')


        class Serializer(serializers.Serializer):
            meta = serializers.JSONField()

        当 view 获取 serializer 时，无论action时什么获取到的 Serializer.meta 是 serializers.JSONField(),

        但我们希望:
            当 view.action = A 时，获取到的 Serializer.meta 是 MetaASerializerMetaASerializer()
            当 view.action = B 时，获取到的 Serializer.meta 是 MetaBSerializerMetaASerializer()

分析:
    问题关键在于数据的映射
    使用 dict 可以解决，但操作起来比较复杂
    所以使用 tree 的结构来实现


方案:
    view:
        使用元类 MetaClass: 在 View 中动态创建所需要的 Serializer

    serializer:
        实现 DictSerializer: 在 Serializer 中定义 JSONField 字段的映射关系
        实现 TreeSerializer: 将 DictSerializer 中定义的映射关系转换为 Tree 的结构
        实现 DictSerializerMetaClass: 在 View 中用来动态创建 Serializer

实现:
    1. 重写 View 的 get_serializer_class 方法, 实现动态创建 Serializer
    2. 实现 TreeSerializer, 将 DictSerializer 中的 dict 数据结构转化为 tree 的数据结构
    3. 实现 DictSerializer, 使用 dict 类型来定义映射关系 (*注意: 继承 TreeSerializer)
    4. 实现 DictSerializerMetaClass, 定义如何创建包含字段类型为 TreeSerializer 的 Serializer

"""

from rest_framework.serializers import Serializer
