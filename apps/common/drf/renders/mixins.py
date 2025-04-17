from django.utils.translation import gettext_noop

from audits.const import ActionChoices
from audits.utils import record_operate_log_and_activity_log
from common.utils import get_logger


logger = get_logger(__file__)


class LogMixin(object):
    @staticmethod
    def _clean_params(query_params):
        clean_params = {}
        ignore_params = ('format', 'order')
        for key, value in dict(query_params).items():
            if key in ignore_params:
                continue
            if isinstance(value, list):
                value = list(filter(None, value))
            if value:
                clean_params[key] = value
        return clean_params

    @staticmethod
    def _get_model(view):
        model = getattr(view, 'model', None)
        if not model:
            serializer = view.get_serializer()
            if serializer:
                model = serializer.Meta.model
        return model

    @staticmethod
    def _build_after(params, data):
        base = {
            gettext_noop('Resource count'): {'value': len(data)}
        }
        extra = {key: {'value': value} for key, value in params.items()}
        return {**extra, **base}

    @staticmethod
    def get_resource_display(params):
        spm_filter = params.pop("spm", None)
        if not params and not spm_filter:
            display_message = gettext_noop("Export all")
        elif spm_filter:
            display_message = gettext_noop("Export only selected items")
        else:
            display_message = gettext_noop("Export filtered")
        return display_message

    def record_logs(self, request, view, data):
        activity_ids, activity_detail = [], ''
        model = self._get_model(view)
        if not model:
            logger.warning('Model is not defined in view: %s' % view)
            return

        params = self._clean_params(request.query_params)
        resource_display = self.get_resource_display(params)
        after = self._build_after(params, data)
        if hasattr(view, 'get_activity_detail_msg'):
            activity_detail = view.get_activity_detail_msg()
            activity_ids = [d['id'] for d in data if 'id' in d]
        record_operate_log_and_activity_log(
            activity_ids, ActionChoices.export, activity_detail,
            model, resource_display=resource_display, after=after
        )
