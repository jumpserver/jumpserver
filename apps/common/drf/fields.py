from uuid import UUID

from rest_framework.fields import get_attribute
from rest_framework.relations import ManyRelatedField, PrimaryKeyRelatedField, MANY_RELATION_KWARGS


class GroupConcatedManyRelatedField(ManyRelatedField):
    def get_attribute(self, instance):
        if hasattr(instance, 'pk') and instance.pk is None:
            return []

        attr = self.source_attrs[-1]

        # `gc` 是 `GroupConcat` 的缩写
        gc_attr = f'gc_{attr}'
        if hasattr(instance, gc_attr):
            gc_value = getattr(instance, gc_attr)
            if isinstance(gc_value, str):
                return [UUID(pk) for pk in set(gc_value.split(','))]
            else:
                return ''

        relationship = get_attribute(instance, self.source_attrs)
        return relationship.all() if hasattr(relationship, 'all') else relationship


class GroupConcatedPrimaryKeyRelatedField(PrimaryKeyRelatedField):
    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return GroupConcatedManyRelatedField(**list_kwargs)

    def to_representation(self, value):
        if self.pk_field is not None:
            return self.pk_field.to_representation(value.pk)

        if hasattr(value, 'pk'):
            return value.pk
        else:
            return value


class CharPrimaryKeyRelatedField(PrimaryKeyRelatedField):
    """ 外键序列化为字符串 """

    def to_internal_value(self, data):
        instance = super().to_internal_value(data)
        return str(instance.id)

    def to_representation(self, value):
        # value is instance.id
        if self.pk_field is not None:
            return self.pk_field.to_representation(value)
        return value