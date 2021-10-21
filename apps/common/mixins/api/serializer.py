# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models.signals import m2m_changed
from rest_framework.request import Request

__all__ = ['SerializerMixin', 'RelationMixin']


class SerializerMixin:
    """ 根据用户请求动作的不同，获取不同的 `serializer_class `"""

    action: str
    request: Request

    serializer_classes = None
    single_actions = ['put', 'retrieve', 'patch']

    def get_serializer_class_by_view_action(self):
        if not hasattr(self, 'serializer_classes'):
            return None
        if not isinstance(self.serializer_classes, dict):
            return None

        view_action = self.request.query_params.get('action') or self.action or 'list'
        serializer_class = self.serializer_classes.get(view_action)

        if serializer_class is None:
            view_method = self.request.method.lower()
            serializer_class = self.serializer_classes.get(view_method)

        if serializer_class is None and view_action in self.single_actions:
            serializer_class = self.serializer_classes.get('single')
        if serializer_class is None:
            serializer_class = self.serializer_classes.get('display')
        if serializer_class is None:
            serializer_class = self.serializer_classes.get('default')
        return serializer_class

    def get_serializer_class(self):
        serializer_class = self.get_serializer_class_by_view_action()
        if serializer_class is None:
            serializer_class = super().get_serializer_class()
        return serializer_class


class RelationMixin:
    m2m_field = None
    from_field = None
    to_field = None
    to_model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assert self.m2m_field is not None, '''
        `m2m_field` should not be `None`
        '''

        self.from_field = self.m2m_field.m2m_field_name()
        self.to_field = self.m2m_field.m2m_reverse_field_name()
        self.to_model = self.m2m_field.related_model
        self.through = getattr(self.m2m_field.model, self.m2m_field.attname).through

    def get_queryset(self):
        # 注意，此处拦截了 `get_queryset` 没有 `super`
        queryset = self.through.objects.all()
        return queryset

    def send_m2m_changed_signal(self, instances, action):
        if not isinstance(instances, list):
            instances = [instances]

        from_to_mapper = defaultdict(list)

        for i in instances:
            to_id = getattr(i, self.to_field).id
            # TODO 优化，不应该每次都查询数据库
            from_obj = getattr(i, self.from_field)
            from_to_mapper[from_obj].append(to_id)

        for from_obj, to_ids in from_to_mapper.items():
            m2m_changed.send(
                sender=self.through, instance=from_obj, action=action,
                reverse=False, model=self.to_model, pk_set=to_ids
            )

    def perform_create(self, serializer):
        instance = serializer.save()
        self.send_m2m_changed_signal(instance, 'post_add')

    def perform_destroy(self, instance):
        instance.delete()
        self.send_m2m_changed_signal(instance, 'post_remove')
