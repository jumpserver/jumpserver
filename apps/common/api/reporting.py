from django.conf import settings

__all__ = ['ReportExportMixin']


class ReportExportMixin:
    report_export_mode_param = 'export_mode'
    report_export_mode_value = 'report'
    report_exporter_class = None

    def get_report_exporter_class(self):
        return getattr(self, 'report_exporter_class', None)

    def should_export_report(self):
        exporter_class = self.get_report_exporter_class()
        if not exporter_class:
            return False
        if getattr(self, 'action', None) != 'list':
            return False
        if self.request.query_params.get('format') != 'xlsx':
            return False
        return self.request.query_params.get(self.report_export_mode_param) == self.report_export_mode_value

    def get_report_export_queryset(self, queryset):
        try:
            return queryset[:settings.MAX_LIMIT_PER_PAGE]
        except TypeError:
            return list(queryset)[:settings.MAX_LIMIT_PER_PAGE]

    def export_report_response(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = self.get_report_export_queryset(queryset)
        exporter_class = self.get_report_exporter_class()
        exporter = exporter_class(view=self, request=request, queryset=queryset)
        response = exporter.get_response()
        exporter.record_logs()
        return response

    def list(self, request, *args, **kwargs):
        if self.should_export_report():
            return self.export_report_response(request, *args, **kwargs)
        return super().list(request, *args, **kwargs)
