from openpyxl import Workbook
from openpyxl.writer.excel import save_virtual_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

from settings.utils import get_login_title
from .base import BaseFileRenderer


class ExcelFileRenderer(BaseFileRenderer):
    media_type = "application/xlsx"
    format = "xlsx"

    wb = None
    ws = None
    row_count = 0

    def initial_writer(self):
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.freeze_panes = 'A2'

    def write_row(self, row):
        self.row_count += 1
        column_count = 0
        for cell_value in row:
            # 处理非法字符
            column_count += 1
            cell_value = ILLEGAL_CHARACTERS_RE.sub(r'', cell_value)
            self.ws.cell(row=self.row_count, column=column_count, value=cell_value)

    def _auto_adjust_column_width(self):
        def calc_handler(x):
            return len(x.encode()) if x else 0

        pre_rows = self.ws.iter_cols(min_row=1, max_row=2, values_only=True)
        # 计算出前两行中最宽的长度
        column_width = [max(map(calc_handler, i)) for i in pre_rows]
        # 调整首行宽度
        for i, width in enumerate(column_width, 1):
            width = width + 2 if width < 98 else 100
            letter = get_column_letter(i)
            self.ws.column_dimensions[letter].width = width

    def get_rendered_value(self):
        self._auto_adjust_column_width()
        value = save_virtual_workbook(self.wb)
        return value

    def _add_column_style(self, col_index, choices, choice_limit=True):
        if isinstance(choices, dict):
            col = get_column_letter(col_index)
            formula1, c_text, c_text_len = '', '', 0
            for key, value in choices.items():
                one = '{} => {}\r\n'.format(key.strip("'"), value)
                c_text += one
                formula1 += '{},'.format(key)
                if len(one.encode()) > c_text_len:
                    c_text_len = len(one.encode())

            if choice_limit:
                dv = DataValidation(
                    type="list", formula1='"{}"'.format(formula1),
                    sqref=('{col}2:{col}1048576'.format(col=col),)
                )
                self.ws.add_data_validation(dv)
            comment = Comment(
                c_text, get_login_title(),
                height=(len(choices) + 1) * 20,
                width=c_text_len * 10
            )
            self.ws['{}1'.format(col)].comment = comment

    def write_column_titles(self, column_titles):
        titles = []
        for i, t in enumerate(column_titles, 1):
            name, choices, choice_limit = t['name'], t['choices'], t['choice_limit']
            self._add_column_style(i, choices, choice_limit)
            titles.append(name)
        self.write_row(titles)
