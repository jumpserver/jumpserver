from rest_framework.response import Response
from rest_framework import status
from django.utils import translation
from django.utils.translation import gettext_noop

from audits.const import ActionChoices
from common.views.mixins import RecordViewLogMixin
from common.utils import i18n_fmt


class AccountRecordViewLogMixin(RecordViewLogMixin):
    get_object: callable
    get_queryset: callable

    @staticmethod
    def _filter_params(params):
        new_params = {}
        need_pop_params = ('format', 'order')
        for key, value in params.items():
            if key in need_pop_params:
                continue
            if isinstance(value, list):
                value = list(filter(None, value))
            if value:
                new_params[key] = value
        return new_params

    def get_resource_display(self, request):
        query_params = dict(request.query_params)
        params = self._filter_params(query_params)

        spm_filter = params.pop("spm", None)

        if not params and not spm_filter:
            display_message = gettext_noop("Export all")
        elif spm_filter:
            display_message = gettext_noop("Export only selected items")
        else:
            query = ",".join(
                ["%s=%s" % (key, value) for key, value in params.items()]
            )
            display_message = i18n_fmt(gettext_noop("Export filtered: %s"), query)
        return display_message

    @property
    def detail_msg(self):
        return i18n_fmt(
            gettext_noop('User %s view/export secret'), self.request.user
        )

    def list(self, request, *args, **kwargs):
        list_func = getattr(super(), 'list')
        if not callable(list_func):
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        response = list_func(request, *args, **kwargs)
        with translation.override('en'):
            resource_display = self.get_resource_display(request)
            ids = [q.id for q in self.get_queryset()]
            self.record_logs(
                ids, ActionChoices.view, self.detail_msg, resource_display=resource_display
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        retrieve_func = getattr(super(), 'retrieve')
        if not callable(retrieve_func):
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        response = retrieve_func(request, *args, **kwargs)
        with translation.override('en'):
            resource = self.get_object()
            self.record_logs(
                [resource.id], ActionChoices.view, self.detail_msg, resource=resource
            )
        return response

