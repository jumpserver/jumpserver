# -*- coding: utf-8 -*-
#
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages

from ..const import KEY_CACHE_RESOURCES_ID

__all__ = [
    "JSONResponseMixin", "IDInCacheFilterMixin", "IDExportFilterMixin",
    "IDInFilterMixin", "ApiMessageMixin"
]


class JSONResponseMixin(object):
    """JSON mixin"""
    @staticmethod
    def render_json_response(context):
        return JsonResponse(context)


class IDInFilterMixin(object):
    def filter_queryset(self, queryset):
        queryset = super(IDInFilterMixin, self).filter_queryset(queryset)
        id_list = self.request.query_params.get('id__in')
        if id_list:
            import json
            try:
                ids = json.loads(id_list)
            except Exception as e:
                return queryset
            if isinstance(ids, list):
                queryset = queryset.filter(id__in=ids)
        return queryset


class IDInCacheFilterMixin(object):

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        spm = self.request.query_params.get('spm')
        if not spm:
            return queryset
        cache_key = KEY_CACHE_RESOURCES_ID.format(spm)
        resources_id = cache.get(cache_key)
        if resources_id and isinstance(resources_id, list):
            queryset = queryset.filter(id__in=resources_id)
        return queryset


class IDExportFilterMixin(object):
    def filter_queryset(self, queryset):
        # 下载导入模版
        if self.request.query_params.get('template') == 'import':
            return []
        else:
            return super(IDExportFilterMixin, self).filter_queryset(queryset)


class ApiMessageMixin:
    success_message = _("%(name)s was %(action)s successfully")
    _action_map = {"create": _("create"), "update": _("update")}

    def get_success_message(self, cleaned_data):
        if not isinstance(cleaned_data, dict):
            return ''
        data = {k: v for k, v in cleaned_data.items()}
        action = getattr(self, "action", "create")
        data["action"] = self._action_map.get(action)
        try:
            message = self.success_message % data
        except:
            message = ''
        return message

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)
        if request.method.lower() in ("get", "delete", "patch"):
            return resp
        if resp.status_code >= 400:
            return resp
        message = self.get_success_message(resp.data)
        if message:
            messages.success(request, message)
        return resp
