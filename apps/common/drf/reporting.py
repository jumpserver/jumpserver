import json
import pickle
from collections import Counter, OrderedDict
from datetime import date, datetime, time
from heapq import nsmallest
from io import BytesIO
from tempfile import TemporaryFile

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.drf.renders.excel import ExcelFileRenderer, ILLEGAL_CHARACTERS_RE
from common.drf.renders.mixins import LogMixin


class ReportRecordSnapshot:
    """Replay the records actually read without retaining every ORM object.

    This private, automatically deleted file only contains pickles written by
    this instance. It is never populated from an upload or a caller's path.
    It stabilizes the rows between the summary/data passes, not the database
    while the bounded queries are initially being read.
    """

    def __init__(self, queryset, limit, batch_size=500):
        self._file = TemporaryFile(mode='w+b')
        self._offsets = []
        self._count = 0
        try:
            for batch in self._read_batches(queryset, limit, batch_size):
                if not batch:
                    continue
                self._offsets.append(self._file.tell())
                pickle.dump(batch, self._file, protocol=pickle.HIGHEST_PROTOCOL)
                self._count += len(batch)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _read_batches(queryset, limit, batch_size):
        if isinstance(queryset, QuerySet) and not getattr(queryset, 'custom', False):
            # Freeze only ordered primary keys, not the much larger model and
            # serializer graphs. Later inserts/deletes cannot shift OFFSETs;
            # rows deleted before their batch is read are simply omitted.
            keys = list(queryset.values_list('pk', flat=True)[:limit])
            source = queryset.all()
            source.query.clear_limits()
            for start in range(0, len(keys), batch_size):
                current = keys[start:start + batch_size]
                objects = {obj.pk: obj for obj in source.filter(pk__in=current)}
                yield [objects[key] for key in current if key in objects]
            return
        for start in range(0, limit, batch_size):
            batch = list(queryset[start:min(start + batch_size, limit)])
            if not batch:
                break
            yield batch
            if len(batch) < batch_size:
                break

    def __len__(self):
        return self._count

    def iter_batches(self):
        for offset in self._offsets:
            self._file.seek(offset)
            # The input is our own private temporary file, never user data.
            yield pickle.load(self._file)

    def __iter__(self):
        for batch in self.iter_batches():
            yield from batch

    def close(self):
        self._file.close()


class ReportAuditRows:
    def __init__(self, count, ids):
        self.count = count
        self.ids = ids

    def __len__(self):
        return self.count

    def __iter__(self):
        return ({'id': value} for value in self.ids)


class BaseListReportExporter:
    format = 'xlsx'
    data_sheet_name = _('Data')
    summary_sheet_name = _('Summary')
    report_title = _('Report')
    report_basename = ''
    max_rows = settings.MAX_LIMIT_PER_PAGE
    min_column_width = 12
    max_column_width = 48

    header_fill = '#D9EAF7'
    section_fill = '#EAF4EA'
    filter_label_map = {
        'date_from': _('Date from'),
        'date_to': _('Date to'),
    }

    def __init__(self, *, view, request, queryset):
        self.view = view
        self.request = request
        self.queryset = queryset
        self.serializer = self.view.get_serializer([], many=True)
        self.export_serializer = getattr(self.serializer, 'child', self.serializer)
        self.render_helper = self._get_render_helper()
        self.records = self._materialize_records(queryset)
        self._exported_count = 0
        self._activity_ids = []

    def _materialize_records(self, queryset):
        return ReportRecordSnapshot(queryset, self.max_rows)

    def _get_render_helper(self):
        helper = ExcelFileRenderer()
        helper.serializer = self.export_serializer
        helper.template = 'export'
        return helper

    def _sanitize_value(self, value):
        if value is None:
            return '-'
        if isinstance(value, Promise):
            value = force_str(value)
        elif not isinstance(value, (str, int, float, bool, datetime, date, time)):
            value = force_str(value)
        if isinstance(value, str):
            return ILLEGAL_CHARACTERS_RE.sub('', value)
        return value

    def _get_cell_format(self, *, bold=False, fill=None, section=False, value=None):
        number_format = None
        if isinstance(value, datetime):
            number_format = 'yyyy-mm-dd h:mm:ss'
        elif isinstance(value, date):
            number_format = 'yyyy-mm-dd'
        elif isinstance(value, time):
            number_format = 'h:mm:ss'
        key = (bold, fill, section, number_format)
        if key not in self._formats:
            properties = {'valign': 'top', 'text_wrap': True}
            if bold or section:
                properties['bold'] = True
            if fill:
                properties['bg_color'] = fill
            if section:
                properties['font_size'] = 12
            if number_format:
                properties['num_format'] = number_format
            self._formats[key] = self._workbook.add_format(properties)
        return self._formats[key]

    def _write_row(self, worksheet, row_index, values, *, bold=False, fill=None):
        lengths = self._column_lengths.setdefault(worksheet, {})
        for column_index, value in enumerate(values):
            value = self._sanitize_value(value)
            cell_format = self._get_cell_format(bold=bold, fill=fill, value=value)
            lengths[column_index] = max(lengths.get(column_index, 0), len(str(value)))
            if isinstance(value, str):
                worksheet.write_string(row_index - 1, column_index, value, cell_format)
            elif isinstance(value, (datetime, date, time)):
                worksheet.write_datetime(row_index - 1, column_index, value, cell_format)
            else:
                worksheet.write(row_index - 1, column_index, value, cell_format)
        return row_index + 1

    def _write_section_title(self, worksheet, row_index, title, width):
        width = max(width, 2)
        cell_format = self._get_cell_format(fill=self.section_fill, section=True)
        worksheet.merge_range(row_index - 1, 0, row_index - 1, width - 1, '', cell_format)
        title = self._sanitize_value(str(title))
        worksheet.write_string(row_index - 1, 0, title, cell_format)
        lengths = self._column_lengths.setdefault(worksheet, {})
        lengths[0] = max(lengths.get(0, 0), len(title))
        for column in range(1, width):
            lengths.setdefault(column, 0)
        return row_index + 1

    def _auto_fit(self, worksheet):
        for column, length in self._column_lengths.get(worksheet, {}).items():
            width = max(self.min_column_width, min(length + 2, self.max_column_width))
            # openpyxl stored this width directly. XlsxWriter adds Excel's
            # five-pixel padding to character widths; use pixels to preserve
            # the existing serialized widths for the default Calibri font.
            worksheet.set_column_pixels(column, column, width * 7)

    def _format_query_params(self):
        params = LogMixin._clean_params(self.request.query_params)
        if not params:
            return _('All data')
        items = []
        for key, value in params.items():
            if isinstance(value, list):
                value = ', '.join([str(item) for item in value])
            elif isinstance(value, (dict, OrderedDict)):
                value = json.dumps(value, ensure_ascii=False)
            label = self.get_filter_label(key)
            items.append(f'{label}={value}')
        return '; '.join(items)

    def get_filter_label(self, key):
        label = self.filter_label_map.get(key)
        if label is not None:
            return force_str(label)
        fields = getattr(self.export_serializer, 'fields', {})
        field = fields.get(key)
        if field is not None and getattr(field, 'label', None):
            return force_str(field.label)
        return key

    def get_report_basename(self):
        if self.report_basename:
            return self.report_basename
        model = getattr(self.view, 'model', None)
        if model is not None:
            return f'{model.__name__.lower()}_report'
        return 'report'

    def get_filename(self):
        suffix = timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        return f'{self.get_report_basename()}_{suffix}.{self.format}'

    def get_response(self):
        try:
            workbook = self.build_workbook()
            workbook.close()
            content = self._workbook_buffer.getvalue()
        finally:
            self.records.close()
            workbook = getattr(self, '_workbook', None)
            try:
                if workbook is not None and not workbook.fileclosed:
                    workbook.close()
            finally:
                buffer = getattr(self, '_workbook_buffer', None)
                if buffer is not None:
                    buffer.close()
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.get_filename()}"'
        return response

    def record_logs(self):
        rows = ReportAuditRows(self._exported_count, self._activity_ids)
        LogMixin().record_logs(self.request, self.view, rows)

    def get_data_sheet_headers(self):
        fields = self.render_helper.get_rendered_fields()
        headers = [str(title) for title in self.render_helper.get_column_titles(fields)]
        return fields, headers

    def get_data_sheet_rows(self):
        fields, headers = self.get_data_sheet_headers()

        def rows():
            self._exported_count = 0
            self._activity_ids = []
            needs_activity_ids = hasattr(self.view, 'get_activity_detail_msg')
            for batch in self.records.iter_batches():
                serializer = self.view.get_serializer(batch, many=True)
                for row in self.render_helper.process_data(serializer.data):
                    current = []
                    for field in fields:
                        field._row = row
                        current.append(self.render_helper.render_value(field, row.get(field.field_name)))
                    self._exported_count += 1
                    if needs_activity_ids and 'id' in row:
                        self._activity_ids.append(row['id'])
                    yield current

        return headers, rows()

    def get_summary_metadata(self):
        return OrderedDict([
            (_('Report'), self.report_title),
            (_('Generated at'), timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')),
            (_('Exported rows'), len(self.records)),
            (_('Filters'), self._format_query_params()),
        ])

    def get_summary_sections(self):
        return []

    def build_workbook(self):
        from xlsxwriter import Workbook

        self._workbook_buffer = BytesIO()
        workbook = self._workbook = Workbook(self._workbook_buffer, {'constant_memory': True})
        self._formats = {}
        self._column_lengths = {}
        summary_sheet = workbook.add_worksheet(str(self.summary_sheet_name))
        self.build_summary_sheet(summary_sheet)

        data_sheet = workbook.add_worksheet(str(self.data_sheet_name))
        self.build_data_sheet(data_sheet)
        return workbook

    def build_data_sheet(self, worksheet):
        headers, rows = self.get_data_sheet_rows()
        next_row = self._write_row(worksheet, 1, headers, bold=True, fill=self.header_fill)
        for row in rows:
            next_row = self._write_row(worksheet, next_row, row)
        worksheet.freeze_panes(1, 0)
        self._auto_fit(worksheet)

    def build_summary_sheet(self, worksheet):
        row_index = 1
        metadata = list(self.get_summary_metadata().items())
        row_index = self._write_section_title(worksheet, row_index, _('Report Summary'), 2)
        for key, value in metadata:
            row_index = self._write_row(worksheet, row_index, [key, value])
        row_index += 1

        for section in self.get_summary_sections():
            section_type = section.get('type')
            title = section.get('title', '')
            if section_type == 'key_value':
                rows = list(section.get('rows', []))
                row_index = self._write_section_title(worksheet, row_index, title, 2)
                for key, value in rows:
                    row_index = self._write_row(worksheet, row_index, [key, value])
            elif section_type == 'table':
                headers = list(section.get('headers', []))
                rows = list(section.get('rows', []))
                row_index = self._write_section_title(worksheet, row_index, title, len(headers))
                if headers:
                    row_index = self._write_row(worksheet, row_index, headers, bold=True, fill=self.header_fill)
                for values in rows:
                    row_index = self._write_row(worksheet, row_index, values)
            row_index += 1

        self._auto_fit(worksheet)

    @staticmethod
    def build_key_value_section(title, rows):
        return {
            'type': 'key_value',
            'title': title,
            'rows': list(rows),
        }

    @staticmethod
    def build_table_section(title, headers, rows):
        return {
            'type': 'table',
            'title': title,
            'headers': list(headers),
            'rows': list(rows),
        }

    @staticmethod
    def build_counter_rows(counter, *, top_n=None):
        sort_key = lambda item: (-item[1], str(item[0]))
        if top_n is not None:
            items = nsmallest(top_n, counter.items(), key=sort_key)
        else:
            items = sorted(counter.items(), key=sort_key)
        return [[key, value] for key, value in items]

    @staticmethod
    def format_percent(numerator, denominator):
        if not denominator:
            return '0.00%'
        return '{:.2f}%'.format((numerator / denominator) * 100)

    @staticmethod
    def local_date_string(value):
        if isinstance(value, datetime):
            value = timezone.localtime(value)
        else:
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d')

    @staticmethod
    def build_top_counter(values):
        counter = Counter()
        for value in values:
            if value in ('', None):
                continue
            counter[str(value)] += 1
        return counter
