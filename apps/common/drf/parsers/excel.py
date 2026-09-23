from io import BytesIO
from itertools import chain
from xml.etree.ElementTree import ParseError as XMLParseError
from zipfile import ZipFile

import pyexcel
from defusedxml.ElementTree import iterparse
from django.utils.translation import gettext as _
from openpyxl.utils.cell import coordinate_to_tuple, range_boundaries

from common.utils.zip import validate_zip_file

from .base import BaseFileParser


class ExcelFileParser(BaseFileParser):
    media_type = 'text/xlsx'

    MAX_ZIP_FILES = 200
    MAX_XML_SIZE = 20 * 1024 * 1024
    MAX_EXPANDED_SIZE = 50 * 1024 * 1024
    MAX_SHEETS = 20
    MAX_ROWS = 10000
    MAX_COLUMNS = 256
    MAX_CELLS = 200000
    MAX_XML_ELEMENTS = 1000000

    def validate_xml(self, events):
        max_row = max_column = row = column = 0
        cells = merged_cells = elements = sheets = 0
        depth = 0
        row_depth = None
        for event, element in events:
            if event == 'end':
                if depth == row_depth:
                    row_depth = None
                depth -= 1
                element.clear()
                continue
            depth += 1
            elements += 1
            if elements > self.MAX_XML_ELEMENTS:
                raise ValueError(_('Excel worksheet exceeds import limits'))
            tag = element.tag.rsplit('}', 1)[-1]
            if tag == 'row':
                row = int(element.get('r', row + 1))
                column = 0
                row_depth = depth
                max_row = max(max_row, row)
            elif tag == 'c' or (row_depth is not None and depth == row_depth + 1):
                cells += 1
                ref = element.get('r')
                if ref:
                    cell_row, column = coordinate_to_tuple(ref)
                else:
                    cell_row, column = row, column + 1
                max_row = max(max_row, cell_row)
                max_column = max(max_column, column)
            elif tag in ('dimension', 'mergeCell', 'comment'):
                min_col, min_row, end_col, end_row = range_boundaries(element.get('ref', ''))
                if any(value is None or value < 1 for value in (min_col, min_row, end_col, end_row)):
                    raise ValueError(_('Invalid excel worksheet range'))
                if end_col < min_col or end_row < min_row:
                    raise ValueError(_('Invalid excel worksheet range'))
                max_row = max(max_row, end_row)
                max_column = max(max_column, end_col)
                if tag == 'mergeCell':
                    merged_cells += (end_row - min_row + 1) * (end_col - min_col + 1)
            elif tag == 'col' and int(element.get('max', 0)) > self.MAX_COLUMNS:
                raise ValueError(_('Excel worksheet exceeds import limits'))
            elif tag == 'sheet':
                sheets += 1
                if sheets > self.MAX_SHEETS:
                    raise ValueError(_('Too many excel worksheets'))

            # Sparse coordinates and merged ranges also expand into in-memory cells.
            if (max_row > self.MAX_ROWS or max_column > self.MAX_COLUMNS
                    or max_row * max_column > self.MAX_CELLS
                    or cells + merged_cells > self.MAX_CELLS):
                raise ValueError(_('Excel worksheet exceeds import limits'))
        return max_row * max_column, cells + merged_cells, elements, sheets

    def validate_workbook(self, stream_data):
        with ZipFile(BytesIO(stream_data)) as archive:
            infos = validate_zip_file(
                archive, max_files=self.MAX_ZIP_FILES,
                max_single_file_size=self.MAX_XML_SIZE,
                max_total_size=self.MAX_EXPANDED_SIZE,
            )
            sheets = grid_cells = stored_cells = elements = 0
            # Relationships may point to worksheets with arbitrary names/extensions.
            for info in infos:
                if info.is_dir():
                    continue
                with archive.open(info) as source:
                    events = iterparse(source, events=('start', 'end'), forbid_dtd=True)
                    try:
                        _, root = next(events)
                    except (XMLParseError, StopIteration):
                        # Non-XML resources, such as images, are not worksheets.
                        continue
                    grid, cells, xml_elements, xml_sheets = self.validate_xml(
                        chain([('start', root)], events)
                    )
                    sheets += xml_sheets
                    if sheets > self.MAX_SHEETS:
                        raise ValueError(_('Too many excel worksheets'))
                    grid_cells += grid
                    stored_cells += cells
                    elements += xml_elements
                    if (max(grid_cells, stored_cells) > self.MAX_CELLS
                            or elements > self.MAX_XML_ELEMENTS):
                        raise ValueError(_('Excel workbook exceeds import limits'))

    def generate_rows(self, stream_data):
        self.validate_workbook(stream_data)
        try:
            workbook = pyexcel.get_book(file_type='xlsx', file_content=stream_data)
        except Exception:
            raise Exception(_('Invalid excel file'))
        # 默认获取第一个工作表sheet
        sheet = workbook.sheet_by_index(0)
        rows = sheet.rows()
        return rows
