# -*- coding: utf-8 -*-
#
from collections import defaultdict
from itertools import chain
from typing import Callable

from django.db import models
from django.db.models.signals import m2m_changed
from rest_framework.response import Response
from rest_framework.settings import api_settings

from common.drf.filters import (
    IDSpmFilterBackend, CustomFilterBackend, IDInFilterBackend,
    IDNotFilterBackend, NotOrRelFilterBackend, LabelFilterBackend
)
from common.utils import get_logger, lazyproperty
from .action import RenderToJsonMixin
from .serializer import SerializerMixin

__all__ = [
    'CommonApiMixin', 'PaginatedResponseMixin', 'RelationMixin',
    'ExtraFilterFieldsMixin',
]

logger = get_logger(__name__)


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
        return queryset

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        serializer_class = self.get_serializer_class()
        if page and serializer_class and hasattr(serializer_class, 'setup_eager_loading'):
            ids = [str(obj.id) for obj in page]
            page = self.get_queryset().filter(id__in=ids)
            page = serializer_class.setup_eager_loading(page)
            page_mapper = {str(obj.id): obj for obj in page}
            page = [page_mapper.get(_id) for _id in ids if _id in page_mapper]
        return page


class ExtraFilterFieldsMixin:
    """
    额外的 api filter
    """
    default_added_filters = (
        CustomFilterBackend, IDSpmFilterBackend, IDInFilterBackend,
        IDNotFilterBackend, LabelFilterBackend
    )
    filter_backends = api_settings.DEFAULT_FILTER_BACKENDS
    extra_filter_fields = []
    extra_filter_backends = []

    def set_compatible_fields(self):
        """
        兼容老的 filter_fields
        """
        if not hasattr(self, 'filter_fields') and hasattr(self, 'filterset_fields'):
            self.filter_fields = self.filterset_fields

    def get_filter_backends(self):
        self.set_compatible_fields()
        if self.filter_backends != self.__class__.filter_backends:
            return self.filter_backends
        backends = list(chain(
            self.filter_backends,
            self.default_added_filters,
            self.extra_filter_backends,
        ))
        # 这个要放在最后
        backends.append(NotOrRelFilterBackend)
        return backends

    def filter_queryset(self, queryset):
        for backend in self.get_filter_backends():
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset


class OrderingFielderFieldsMixin:
    """
    额外的 api ordering
    """
    ordering_fields = None
    extra_ordering_fields = []

    @lazyproperty
    def ordering_fields(self):
        return self._get_ordering_fields()

    def _get_ordering_fields(self):
        if isinstance(self.__class__.ordering_fields, (list, tuple)):
            return self.__class__.ordering_fields

        try:
            valid_fields = self.get_valid_ordering_fields()
        except Exception as e:
            logger.debug('get_valid_ordering_fields error: %s, pass' % e)
            # 这里千万不要这么用，会让 logging 重复，至于为什么，我也不知道
            # logging.debug('get_valid_ordering_fields error: %s' % e)
            valid_fields = []

        fields = list(chain(
            valid_fields,
            self.extra_ordering_fields
        ))
        return fields

    def get_valid_ordering_fields(self):
        if getattr(self, 'model', None):
            model = self.model
        elif getattr(self, 'queryset', None):
            model = self.queryset.model
        else:
            queryset = self.get_queryset()
            if isinstance(queryset, list):
                model = None
            else:
                model = queryset.model

        if not model:
            return []

        excludes_fields = (
            models.UUIDField, models.Model, models.ForeignKey,
            models.FileField, models.JSONField, models.ManyToManyField,
            models.DurationField,
        )
        valid_fields = []
        for field in model._meta.fields:
            if isinstance(field, excludes_fields):
                continue
            valid_fields.append(field.name)
        return valid_fields


class CommonApiMixin(
    SerializerMixin, ExtraFilterFieldsMixin, OrderingFielderFieldsMixin,
    QuerySetMixin, RenderToJsonMixin, PaginatedResponseMixin
):
    def is_swagger_request(self):
        return getattr(self, 'swagger_fake_view', False) or \
            getattr(self, 'raw_action', '') == 'metadata'
