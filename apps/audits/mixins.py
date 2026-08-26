from django.utils import translation
from django.utils.translation import gettext_noop

from rest_framework.exceptions import ValidationError
from rest_framework.fields import DateTimeField

from common.utils import i18n_fmt
from common.utils.timezone import as_current_tz
from .const import ActionChoices
from .handler import create_or_update_operate_log


class RecordViewLogMixin:
    record_view_log_actions = ('retrieve',)
    record_view_log_query_params = ()
    record_view_log_datetime_field = None

    @staticmethod
    def _format_view_log_datetime(value, include_seconds=False):
        if not value:
            return None
        try:
            value = DateTimeField().to_internal_value(value)
        except (TypeError, ValueError, ValidationError):
            return None
        fmt = '%Y-%m-%d %H:%M:%S' if include_seconds else '%Y-%m-%d %H:%M'
        return as_current_tz(value).strftime(fmt)

    def _build_view_log_resource_display(
            self, resource_type, query_params, count, data
    ):
        dates = []
        if self.record_view_log_datetime_field:
            dates = [
                self._format_view_log_datetime(
                    item.get(self.record_view_log_datetime_field),
                    include_seconds=True
                )
                for item in data if isinstance(item, dict)
            ]
            dates = sorted(filter(None, dates))

        date_from = dates[0] if dates else self._format_view_log_datetime(
            query_params.get('date_from')
        )
        date_to = dates[-1] if dates else self._format_view_log_datetime(
            query_params.get('date_to')
        )
        count_label = gettext_noop('Resource count')

        if date_from and date_to:
            return i18n_fmt(
                '%s: %s ~ %s, %s: %s', resource_type, date_from, date_to,
                count_label, count
            )
        if date_from:
            return i18n_fmt(
                '%s: %s: %s, %s: %s', resource_type,
                gettext_noop('Date from'), date_from, count_label, count
            )
        if date_to:
            return i18n_fmt(
                '%s: %s: %s, %s: %s', resource_type,
                gettext_noop('Date to'), date_to, count_label, count
            )
        return i18n_fmt(
            '%s: %s, %s: %s', resource_type, gettext_noop('All'),
            count_label, count
        )

    def _get_view_log_data(self, response):
        data = getattr(response, 'data', None)
        if isinstance(data, dict) and 'results' in data:
            data = data['results']
        elif isinstance(data, dict):
            data = [data]
        if not isinstance(data, (list, tuple)):
            return []
        return data

    def _get_view_log_metadata(self, query_params, count):
        metadata = {}
        for key in self.record_view_log_query_params:
            values = list(filter(None, query_params.getlist(key)))
            if not values:
                continue
            value = values[0] if len(values) == 1 else values
            metadata[key] = {'value': value}
        metadata['Resource count'] = {'value': count}
        return metadata

    def record_view_log(self, request, response, resource=None):
        if request.method != 'GET':
            return
        if not 200 <= response.status_code < 300:
            return
        if request.query_params.get('format') in ('csv', 'xlsx'):
            return

        data = self._get_view_log_data(response)
        if not data:
            return

        with translation.override('en'):
            resource_type = getattr(
                self.model._meta, 'verbose_name_raw',
                self.model._meta.verbose_name
            )
            resource_display = None
            if resource is None:
                resource_display = self._build_view_log_resource_display(
                    resource_type, request.query_params, len(data), data
                )
            create_or_update_operate_log(
                ActionChoices.view, resource_type, resource=resource,
                resource_display=resource_display, force=True,
                after=self._get_view_log_metadata(
                    request.query_params, len(data)
                )
            )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if 'list' in self.record_view_log_actions:
            self.record_view_log(request, response)
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if (
                'retrieve' in self.record_view_log_actions
                and 200 <= response.status_code < 300
                and self._get_view_log_data(response)
        ):
            self.record_view_log(
                request, response, resource=self.get_object()
            )
        return response
