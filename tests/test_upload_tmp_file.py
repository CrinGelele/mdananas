import csv
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from mdananas.upload_tmp_file import bulk_insert_to_sqlserver, upload_file


class BulkInvoiceUploadTest(SimpleTestCase):
    def setUp(self):
        self.model = SimpleNamespace(
            _meta=SimpleNamespace(
                db_table='[00_ROOT].[ROOT_TMP_Invoices]',
                fields=[SimpleNamespace(name='customer'), SimpleNamespace(name='shipped_to')],
            )
        )

    def test_bulk_insert_parses_quoted_csv_but_preserves_plain_mode(self):
        with mock.patch('mdananas.upload_tmp_file.connections') as connections, \
             mock.patch('mdananas.upload_tmp_file.os.path.exists', return_value=False):
            bulk_insert_to_sqlserver('invoice.csv', self.model)
            sql = connections['ideal'].cursor.return_value.__enter__.return_value.execute.call_args.args[0]
            self.assertIn("FORMAT = 'CSV'", sql)
            self.assertIn("FIELDQUOTE = '\"'", sql)
            self.assertIn("FIELDTERMINATOR = ';'", sql)

            connections['ideal'].cursor.return_value.__enter__.return_value.execute.reset_mock()
            bulk_insert_to_sqlserver('plain.csv', self.model, plain_csv=True)
            sql = connections['ideal'].cursor.return_value.__enter__.return_value.execute.call_args.args[0]
            self.assertNotIn("FORMAT = 'CSV'", sql)
            self.assertNotIn('FIELDQUOTE', sql)

    def test_invoice_quotes_are_written_as_csv_and_import_uses_csv_mode(self):
        real_named_temporary_file = tempfile.NamedTemporaryFile
        with tempfile.TemporaryDirectory() as directory:
            def local_file(**kwargs):
                return real_named_temporary_file(**{**kwargs, 'dir': directory})

            record = SimpleNamespace(customer='ЛЕНТА ООО', shipped_to='ООО "Лента", РЦ 7114')
            with mock.patch('mdananas.upload_tmp_file.connections'), \
                 mock.patch('mdananas.upload_tmp_file.IdealSchemaEditor'), \
                 mock.patch('mdananas.upload_tmp_file.tempfile.NamedTemporaryFile', side_effect=local_file), \
                 mock.patch('mdananas.upload_tmp_file.bulk_insert_to_sqlserver') as bulk_insert:
                upload_file([record], self.model, '[00_ROOT].[ROOT_PROC_MERGE_Invoices]', big=True)

            path = Path(bulk_insert.call_args.args[0])
            self.assertFalse(bulk_insert.call_args.kwargs['plain_csv'])
            self.assertIn('"ООО ""Лента"", РЦ 7114"', path.read_text(encoding='utf-8'))
            with path.open(encoding='utf-8', newline='') as handle:
                rows = list(csv.reader(handle, delimiter=';'))
            self.assertEqual(rows[1], ['ЛЕНТА ООО', 'ООО "Лента", РЦ 7114'])
