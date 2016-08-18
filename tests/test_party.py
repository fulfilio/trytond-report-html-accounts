# -*- coding: utf-8 -*-
import sys
import unittest
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, with_transaction
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.exceptions import UserError

from test_base import BaseTestCase


class TestParty(BaseTestCase):
    """
    Tests for Account Statement Report
    """
    @with_transaction()
    @unittest.skipIf(sys.platform == 'darwin', 'wkhtmltopdf repo on OSX')
    def test_0010_test_party_account_statement_report_wizard_case_1(self):
        """
        Test the sales report wizard for amount format 'Cr./Dr.'
        """
        ActionReport = POOL.get('ir.action.report')
        ReportWizard = POOL.get(
            'report.party_account_statement.wizard', type="wizard"
        )
        Move = POOL.get('account.move')

        self.setup_defaults()

        report_action, = ActionReport.search([
            ('report_name', '=', 'report.party_account_statement'),
            ('name', '=', 'Account Statement')
        ])
        report_action.extension = 'pdf'
        report_action.save()

        journal_revenue, = self.Journal.search([
            ('code', '=', 'REV'),
        ])

        # Create account moves
        period = self.fiscal_year.periods[0]
        move, = Move.create([{
            'period': period.id,
            'journal': journal_revenue,
            'date': period.start_date,
            'lines': [
                ('create', [{
                    'account': self._get_account_by_kind('revenue').id,
                    'credit': Decimal('42.0'),
                }, {
                    'account': self._get_account_by_kind('receivable').id,
                    'debit': Decimal('42.0'),
                    'date': period.start_date,
                    'maturity_date':
                        period.start_date + relativedelta(days=20),
                    'party': self.party
                }])
            ]
        }])
        Move.post([move])

        with Transaction().set_context({'company': self.company.id}):
            session_id, start_state, end_state = ReportWizard.create()
            result = ReportWizard.execute(session_id, {}, start_state)
            self.assertEqual(result.keys(), ['view'])
            self.assertEqual(result['view']['buttons'], [
                {
                    'state': 'end',
                    'states': '{}',
                    'icon': 'tryton-cancel',
                    'default': False,
                    'string': 'Cancel',
                }, {
                    'state': 'generate',
                    'states': '{}',
                    'icon': 'tryton-ok',
                    'default': True,
                    'string': 'Generate',
                }
            ])
            data = {
                start_state: {
                    'start_date': period.start_date,
                    'end_date': period.start_date + relativedelta(days=30),
                    'consider_maturity_date': True,
                    'hide_reconciled_lines': False,
                    'amount_format': 'cr/dr',
                },
            }

            result = ReportWizard.execute(
                session_id, data, 'generate'
            )
            self.assertEqual(len(result['actions']), 1)

            report_name = result['actions'][0][0]['report_name']
            report_data = result['actions'][0][1]

            Report = POOL.get(report_name, type="report")

            # Set Pool.test as False as we need the report to be
            # generated as PDF
            # This is specifically to cover the PDF coversion code
            Pool.test = False

            with self.assertRaises(UserError):
                val = Report.execute([], report_data)

            with Transaction().set_context(active_id=self.party.id):
                result = ReportWizard.execute(
                    session_id, data, 'generate'
                )
                self.assertEqual(len(result['actions']), 1)

                report_name = result['actions'][0][0]['report_name']
                report_data = result['actions'][0][1]

                val = Report.execute([], report_data)

                # Revert Pool.test back to True for other tests to run
                # normally
                Pool.test = True

                self.assert_(val)
                # Assert report type
                self.assertEqual(val[0], 'pdf')
                # Assert report name
                self.assertEqual(val[3], 'Account Statement')

    @with_transaction()
    def test_0015_test_party_account_statement_report_wizard_case_2(self):
        """
        Test the sales report wizard for amount format '+/-'
        """
        ActionReport = POOL.get('ir.action.report')
        ReportWizard = POOL.get(
            'report.party_account_statement.wizard', type="wizard"
        )
        Move = POOL.get('account.move')

        self.setup_defaults()

        report_action, = ActionReport.search([
            ('report_name', '=', 'report.party_account_statement'),
            ('name', '=', 'Account Statement')
        ])
        report_action.extension = 'pdf'
        report_action.save()

        journal_revenue, = self.Journal.search([
            ('code', '=', 'REV'),
        ])

        # Create account moves
        period = self.fiscal_year.periods[0]
        move, = Move.create([{
            'period': period.id,
            'journal': journal_revenue,
            'date': period.start_date,
            'lines': [
                ('create', [{
                    'account': self._get_account_by_kind('revenue').id,
                    'credit': Decimal('42.0'),
                }, {
                    'account': self._get_account_by_kind('receivable').id,
                    'debit': Decimal('42.0'),
                    'date': period.start_date,
                    'maturity_date':
                        period.start_date + relativedelta(days=20),
                    'party': self.party
                }])
            ]
        }])
        Move.post([move])

        with Transaction().set_context({'company': self.company.id}):
            session_id, start_state, end_state = ReportWizard.create()
            result = ReportWizard.execute(session_id, {}, start_state)
            self.assertEqual(result.keys(), ['view'])
            self.assertEqual(result['view']['buttons'], [
                {
                    'state': 'end',
                    'states': '{}',
                    'icon': 'tryton-cancel',
                    'default': False,
                    'string': 'Cancel',
                }, {
                    'state': 'generate',
                    'states': '{}',
                    'icon': 'tryton-ok',
                    'default': True,
                    'string': 'Generate',
                }
            ])
            data = {
                start_state: {
                    'start_date': period.start_date,
                    'end_date': period.start_date + relativedelta(days=30),
                    'consider_maturity_date': True,
                    'hide_reconciled_lines': False,
                    'amount_format': '+/-',
                },
            }

            result = ReportWizard.execute(
                session_id, data, 'generate'
            )
            self.assertEqual(len(result['actions']), 1)

            report_name = result['actions'][0][0]['report_name']
            report_data = result['actions'][0][1]

            Report = POOL.get(report_name, type="report")

            # Set Pool.test as False as we need the report to be
            # generated as PDF
            # This is specifically to cover the PDF coversion code
            Pool.test = False

            with self.assertRaises(UserError):
                val = Report.execute([], report_data)

            with Transaction().set_context(active_id=self.party.id):
                result = ReportWizard.execute(
                    session_id, data, 'generate'
                )
                self.assertEqual(len(result['actions']), 1)

                report_name = result['actions'][0][0]['report_name']
                report_data = result['actions'][0][1]

                val = Report.execute([], report_data)

                # Revert Pool.test back to True for other tests to run
                # normally
                Pool.test = True

                self.assert_(val)
                # Assert report type
                self.assertEqual(val[0], 'pdf')
                # Assert report name
                self.assertEqual(val[3], 'Account Statement')

    @with_transaction()
    def test_0020_test_party_balance_for_date_case_1(self):
        """
        Test the party balance for the given date
        """
        Move = POOL.get('account.move')
        Invoice = POOL.get('account.invoice')
        InvoiceLine = POOL.get('account.invoice.line')

        self.setup_defaults()

        current_year = date.today().year
        jan_1 = date(current_year, 1, 1)

        journal_revenue, = self.Journal.search([
            ('code', '=', 'REV'),
        ])
        period = sorted(
            self.fiscal_year.periods,
            key=lambda p: p.start_date
        )[0]

        # Assert that opening and closing balance are 0 on January 1
        self.assertEqual(
            self.party.get_opening_balance_on(jan_1),
            Decimal('0.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_1),
            Decimal('0.0')
        )

        # Create and post an invoice for $100 on Jan 1 for party
        with Transaction().set_context(company=self.company.id):
            invoice, = Invoice.create([{
                'party': self.party,
                'type': 'out',
                'journal': journal_revenue,
                'invoice_address': self.party.address_get(
                    'invoice'),
                'account': self._get_account_by_kind('receivable'),
                'description': 'Test Invoice',
                'payment_term': self.payment_term,
                'invoice_date': jan_1,
            }])

            invoice_line, = InvoiceLine.create([{
                'type': 'line',
                'description': 'Test Line',
                'party': self.party.id,
                'invoice_type': 'out',
                'invoice': invoice.id,
                'unit_price': Decimal('100.0'),
                'quantity': 1,
                'account': self._get_account_by_kind('revenue')
            }])

            Invoice.post([invoice])

        # Assert that opening is 0 and closing balance is $100 on January 1
        self.assertEqual(
            self.party.get_opening_balance_on(jan_1),
            Decimal('0.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_1),
            Decimal('100.0')
        )

        # Pay the above created invoice
        move, = Move.create([{
            'period': period,
            'journal': journal_revenue,
            'date': jan_1,
            'lines': [
                ('create', [{
                    'account': self._get_account_by_kind('other').id,
                    'debit': Decimal('100.0'),
                }, {
                    'account': self._get_account_by_kind('receivable').id,
                    'credit': Decimal('100.0'),
                    'date': jan_1,
                    'party': self.party
                }])
            ]
        }])
        Move.post([move])

        # Assert that opening and closing balance are 0 on January 1
        self.assertEqual(
            self.party.get_opening_balance_on(jan_1),
            Decimal('0.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_1),
            Decimal('0.0')
        )

    @with_transaction()
    def test_0030_test_party_balance_for_date_case_2(self):
        """
        Test the party balance for the given date
        """
        Move = POOL.get('account.move')
        Invoice = POOL.get('account.invoice')
        InvoiceLine = POOL.get('account.invoice.line')

        self.setup_defaults()

        current_year = date.today().year
        jan_1 = date(current_year, 1, 1)

        journal_revenue, = self.Journal.search([
            ('code', '=', 'REV'),
        ])
        period = sorted(
            self.fiscal_year.periods,
            key=lambda p: p.start_date
        )[0]

        # Assert that opening and closing balance are 0 on January 1
        self.assertEqual(
            self.party.get_opening_balance_on(jan_1),
            Decimal('0.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_1),
            Decimal('0.0')
        )

        # Create and post an invoice for $100 on Jan 1 for party
        with Transaction().set_context(company=self.company.id):
            invoice, = Invoice.create([{
                'party': self.party,
                'type': 'out',
                'journal': journal_revenue,
                'invoice_address': self.party.address_get(
                    'invoice'),
                'account': self._get_account_by_kind('receivable'),
                'description': 'Test Invoice',
                'payment_term': self.payment_term,
                'invoice_date': jan_1,
            }])

            invoice_line, = InvoiceLine.create([{
                'type': 'line',
                'description': 'Test Line',
                'party': self.party.id,
                'invoice_type': 'out',
                'invoice': invoice.id,
                'unit_price': Decimal('100.0'),
                'quantity': 1,
                'account': self._get_account_by_kind('revenue')
            }])

            Invoice.post([invoice])

        # Assert that opening is 0 and closing balance is $100 on January 1
        self.assertEqual(
            self.party.get_opening_balance_on(jan_1),
            Decimal('0.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_1),
            Decimal('100.0')
        )

        # Pay the above created invoice on January 2
        jan_2 = jan_1 + relativedelta(days=1)
        move, = Move.create([{
            'period': period,
            'journal': journal_revenue,
            'date': jan_2,
            'lines': [
                ('create', [{
                    'account': self._get_account_by_kind('other').id,
                    'debit': Decimal('100.0'),
                }, {
                    'account': self._get_account_by_kind('receivable').id,
                    'credit': Decimal('100.0'),
                    'date': jan_2,
                    'party': self.party
                }])
            ]
        }])
        Move.post([move])

        # Assert that opening is 0 and closing balance is $100 on January 1
        self.assertEqual(
            self.party.get_opening_balance_on(jan_1),
            Decimal('0.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_1),
            Decimal('100.0')
        )

        # Assert that opening is $100 in Jan 2 and closing balance is
        # $0 on Jan 2
        self.assertEqual(
            self.party.get_opening_balance_on(jan_2),
            Decimal('100.0')
        )
        self.assertEqual(
            self.party.get_balance_on(jan_2),
            Decimal('0.0')
        )

    @with_transaction()
    def test_0040_test_moves_for_fiscal_year(self):
        """
        Test if the moves returned by query are not limited to present
        fiscal year
        """
        Move = POOL.get('account.move')
        PartyAccountStatement = POOL.get(
            'report.party_account_statement', type="report"
        )

        self.setup_defaults()

        # Create a fiscal year for the previous year
        date_ = self.fiscal_year.periods[0].start_date
        date_last_year = date(date_.year - 1, date_.month, date_.day)
        previous_fiscal_year = self._create_fiscal_year(
            date=date_last_year, company=self.company.id
        )

        # Create 2 moves one for each fiscal year
        journal_revenue, = self.Journal.search([
            ('code', '=', 'REV'),
        ])

        move1, = Move.create([{
            'period': self.fiscal_year.periods[0],
            'journal': journal_revenue,
            'date': date_,
            'lines': [
                ('create', [{
                    'account': self._get_account_by_kind('revenue').id,
                    'credit': Decimal('42.0'),
                }, {
                    'account': self._get_account_by_kind('receivable').id,
                    'debit': Decimal('42.0'),
                    'date': date_,
                    'maturity_date': date_,
                    'party': self.party
                }])
            ]
        }])
        Move.post([move1])

        move2, = Move.create([{
            'period': previous_fiscal_year.periods[0],
            'journal': journal_revenue,
            'date': date_last_year,
            'lines': [
                ('create', [{
                    'account': self._get_account_by_kind('revenue').id,
                    'credit': Decimal('42.0'),
                }, {
                    'account': self._get_account_by_kind('receivable').id,
                    'debit': Decimal('42.0'),
                    'date': date_last_year,
                    'maturity_date': date_last_year,
                    'party': self.party
                }])
            ]
        }])
        Move.post([move2])

        moves = PartyAccountStatement.get_move_lines_maturing(
            self.party, date_last_year, date_
        )

        # Assert if moves of both fiscal year are returned
        self.assertEqual(len(moves), 2)

        # Test for previous failing condition when the moves
        # of current fiscal year were returned
        with Transaction().set_context(date=date_):
            moves = PartyAccountStatement.get_move_lines_maturing(
                self.party, date_last_year, date_
            )

            # Assert if moves of current fiscal year are returned
            self.assertEqual(len(moves), 1)


def suite():
    "Define suite"
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestParty)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
