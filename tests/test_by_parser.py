from unittest import mock

import pandas as pd
from django.test import SimpleTestCase, RequestFactory
from export_service.views.by_views import get_file_year, process_sales_file


class RowInfo:
    def __init__(self, outline_level):
        self.outline_level = outline_level


class FakeSheet:
    nrows = 10
    ncols = 18
    rowinfo_map = {6: RowInfo(0), 7: RowInfo(1), 8: RowInfo(2), 9: RowInfo(3)}

    def cell_value(self, i, j):
        if i == 3 and j == 6:
            return 'март 2027 г.'
        return ''


class FakeBook:
    def sheet_by_index(self, index):
        return FakeSheet()


class BYParserTest(SimpleTestCase):
    def test_file_year(self):
        self.assertEqual(get_file_year(FakeSheet()), 2027)

    @mock.patch('export_service.views.by_views.pd.read_excel')
    @mock.patch('export_service.views.by_views.xlrd.open_workbook')
    def test_sales_parser(self, open_workbook, read_excel):
        open_workbook.return_value = FakeBook()
        data = [[None] * 18 for _ in range(10)]
        data[7][2] = 'Покупатель'
        data[8][2] = 'Магазин'
        data[9][2] = 'Товар'
        data[9][5] = '56451'
        data[9][6] = 36
        data[9][7] = 1324.08
        data[6][6] = 36
        data[6][7] = 1324.08
        for month in range(4, 9):
            data[6][2 * month] = 0
            data[6][2 * month + 1] = 0
        read_excel.return_value = pd.DataFrame(data)
        request = RequestFactory().get('/export/by/')
        request.session = mock.Mock(session_key='test')
        records = process_sales_file(mock.Mock(read=lambda: b'file'), request)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].date_year, 2027)
        self.assertEqual(records[0].volume, 36)
        self.assertEqual(records[0].purchase_price_value, 0)
