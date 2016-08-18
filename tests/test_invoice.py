# -*- coding: utf-8 -*-
import sys
import os
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, with_transaction
from trytond.transaction import Transaction
from trytond.pool import Pool

from test_base import BaseTestCase

DIR = os.path.abspath(os.path.normpath(os.path.join(
    __file__, '..', '..', '..', '..', '..', 'trytond'
)))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))


class TestInvoice(BaseTestCase):
    """
    Test Invoice
    """
    @with_transaction()
    @unittest.skipIf(sys.platform == 'darwin', 'wkhtmltopdf repo on OSX')
    def test_0010_test_invoice_report(self):
        """
        Test the invoice report
        """
        ActionReport = POOL.get('ir.action.report')
        Date = POOL.get('ir.date')
        Invoice = POOL.get('account.invoice')

        self.setup_defaults()
        InvoiceReport = POOL.get('account.invoice.html', type='report')

        with Transaction().set_context(company=self.company.id):
            invoice, = Invoice.create([{
                'party': self.party,
                'type': 'out',
                'journal': self.cash_journal,
                'invoice_address': self.party.address_get(
                    'invoice'),
                'description': 'Test Invoice',
                'payment_term': self.payment_term,
                'invoice_date': Date.today(),
                'account': self._get_account_by_kind('receivable'),
                'lines': [('create', [{
                    'type': 'line',
                    'description': 'Test Line',
                    'party': self.party.id,
                    'invoice_type': 'out',
                    'unit_price': Decimal('100.0'),
                    'quantity': 1,
                    'account': self._get_account_by_kind('revenue'),
                }])]
            }])

            # Change the report extension to PDF
            action_report, = ActionReport.search([
                ('name', '=', 'Invoice'),
                ('report_name', '=', 'account.invoice.html')
            ])
            action_report.extension = 'pdf'
            action_report.save()

            # Set Pool.test as False as we need the report to be generated
            # as PDF
            # This is specifically to cover the PDF coversion code
            Pool.test = False

            # Generate Invoice
            val = InvoiceReport.execute([invoice.id], {})

            # Revert Pool.test back to True for other tests to run normally
            Pool.test = True

            self.assert_(val)
            # Assert report name
            self.assertEqual(val[3], 'Invoice')


def suite():
    "Define suite"
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestInvoice)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
