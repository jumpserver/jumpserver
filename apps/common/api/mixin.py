# -*- coding: utf-8 -*-
#
from collections import defaultdict
from typing import Callable

from django.db.models.signals import m2m_changed
from rest_framework.response import Response

from .action import RenderToJsonMixin
from .filter import ExtraFilterFieldsMixin, OrderingFielderFieldsMixin
from .serializer import SerializerMixin

__all__ = [
    'CommonApiMixin', 'PaginatedResponseMixin', 'RelationMixin',
]


class PaginatedResponseMixin:

    def get_paginated_response_from_queryset(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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


class QuerySetMixin:
    action: str
    get_serializer_class: Callable
    get_queryset: Callable

    def get_queryset(self):
        queryset = super().get_queryset()
        if not hasattr(self, 'action'):
            return queryset
        if self.action == 'metadata':
            queryset = queryset.none()
        if self.action in ['list', 'metadata']:
            serializer_class = self.get_serializer_class()
            if serializer_class and hasattr(serializer_class, 'setup_eager_loading'):
                queryset = serializer_class.setup_eager_loading(queryset)
        return queryset


class CommonApiMixin(SerializerMixin, ExtraFilterFieldsMixin, OrderingFielderFieldsMixin,
                     QuerySetMixin, RenderToJsonMixin, PaginatedResponseMixin):
    pass
