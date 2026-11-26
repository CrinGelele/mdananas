import io
from datetime import date

from django.test import SimpleTestCase
from openpyxl import Workbook

from .views.ge_views import write_excel_csv


def convert(workbook, filename, kind):
    source = io.BytesIO()
    workbook.save(source)
    source.name = filename
    source.seek(0)
    output = io.StringIO(newline='')
    write_excel_csv(source, kind, output)
    return output.getvalue()


class GeorgiaExcelTests(SimpleTestCase):
    def test_competitor_report_is_rejected_as_own_sales(self):
        book = Workbook()
        book.active.append(['დასახელება(ინგლისურად)', 'გენერიული დასახელება(ლათინურად)', 'თარიღი',
                            'საქონელი', 'რაოდენობა', 'თანხა', 'საწყობი'])
        book.active.append(['Pear', None, date(2026, 10, 1), 'Gerber Pear', 1, 12, 'Depo 8'])
        with self.assertRaisesMessage(ValueError, 'продажи конкурентов'):
            convert(book, 'Sales.xlsx', 'sales')

    def test_sales_preserves_historical_material_key_and_zero_price(self):
        book = Workbook()
        book.active.append(['დასახელება(ინგლისურად)', 'თარიღი', 'საქონელი', 'რაოდენობა', 'თანხა', 'საწყობი'])
        book.active.append(['Porridge', "'01/10/2026'", 'SKU "Apple"', 2, 0, 'склад '])
        self.assertEqual(convert(book, 'Sales.xlsx', 'sales'),
                         'eng;date;material;sales;value;store_ge\r\n'
                         'Porridge;\'01/10/2026\';"SKU ""Apple""";2;0;склад \r\n')

    def test_stock_uses_sheet_date_for_every_lot(self):
        book = Workbook()
        for title, count in [('03,10', 2), ('10,10', 1)]:
            sheet = book.active if title == '03,10' else book.create_sheet()
            sheet.title = title
            sheet.append(['დასახელება(ინგლისურად)', 'საქონელი', 'ვადა', 'საწყობი', 'რაოდენობა'])
            for lot in range(count):
                sheet.append(['Pear', 'SKU', date(2028, 1, 1 + lot), 'A', 1.5])
        self.assertEqual(convert(book, 'Stock 10.2026.xlsx', 'stock'),
                         'eng;material;store_ge;stock;date\r\n'
                         'Pear;SKU;A;1,5;03.10.2026\r\n'
                         'Pear;SKU;A;1,5;03.10.2026\r\n'
                         'Pear;SKU;A;1,5;10.10.2026\r\n')
