# -*- coding: utf-8 -*-
"""
    tests/test_party.py
    :copyright: (C) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.exceptions import UserError


class TestParty(unittest.TestCase):
    """
    Tests for Account Statement Report
    """

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('report_html_accounts')
        trytond.tests.test_tryton.install_module('account_invoice')

        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Party = POOL.get('party.party')
        self.User = POOL.get('res.user')
        self.Country = POOL.get('country.country')
        self.Subdivision = POOL.get('country.subdivision')
        self.Employee = POOL.get('company.employee')
        self.Journal = POOL.get('account.journal')
        self.Group = POOL.get('res.group')
        self.Country = POOL.get('country.country')
        self.Subdivision = POOL.get('country.subdivision')

    def _create_fiscal_year(self, date=None, company=None):
        """
        Creates a fiscal year and requried sequences
        """
        Sequence = POOL.get('ir.sequence')
        SequenceStrict = POOL.get('ir.sequence.strict')
        FiscalYear = POOL.get('account.fiscalyear')

        if date is None:
            date = datetime.date.today()

        if company is None:
            company, = self.Company.search([], limit=1)

        invoice_sequence, = SequenceStrict.create([{
            'name': '%s' % date.year,
            'code': 'account.invoice',
            'company': company,
        }])
        fiscal_year, = FiscalYear.create([{
            'name': '%s' % date.year,
            'start_date': date + relativedelta(month=1, day=1),
            'end_date': date + relativedelta(month=12, day=31),
            'company': company,
            'post_move_sequence': Sequence.create([{
                'name': '%s' % date.year,
                'code': 'account.move',
                'company': company,
            }])[0],
            'out_invoice_sequence': invoice_sequence,
            'in_invoice_sequence': invoice_sequence,
            'out_credit_note_sequence': invoice_sequence,
            'in_credit_note_sequence': invoice_sequence,
        }])
        FiscalYear.create_period([fiscal_year])
        return fiscal_year

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard")

        account_template, = AccountTemplate.search([
            ('parent', '=', None),
            ('name', '=', 'Minimal Account Chart'),
        ])

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec
        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts[0] if accounts else False

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])

    def setup_defaults(self):
        """Creates default data for testing
        """
        currency, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        with Transaction().set_context(company=None):
            company_party, = self.Party.create([{
                'name': 'Openlabs'
            }])
            employee_party, = self.Party.create([{
                'name': 'Jim'
            }])

        self.company, = self.Company.create([{
            'party': company_party,
            'currency': currency,
        }])

        self.employee, = self.Employee.create([{
            'party': employee_party.id,
            'company': self.company.id,
        }])

        self.User.write([self.User(USER)], {
            'company': self.company,
            'main_company': self.company,
        })

        CONTEXT.update(self.User.get_preferences(context_only=True))

        # Create Fiscal Year
        self.fiscal_year = self._create_fiscal_year(company=self.company.id)
        # Create Chart of Accounts
        self._create_coa_minimal(company=self.company.id)

        self.cash_journal, = self.Journal.search(
            [('type', '=', 'cash')], limit=1
        )
        self.Journal.write([self.cash_journal], {
            'debit_account': self._get_account_by_kind('other').id
        })

        self.country, = self.Country.create([{
            'name': 'United States of America',
            'code': 'US',
        }])

        self.subdivision, = self.Subdivision.create([{
            'country': self.country.id,
            'name': 'California',
            'code': 'CA',
            'type': 'state',
        }])

        # Add address to company's party record
        self.Party.write([self.company.party], {
            'addresses': [('create', [{
                'name': 'Openlabs',
                'party': Eval('id'),
                'city': 'Los Angeles',
                'country': self.country.id,
                'subdivision': self.subdivision.id,
            }])],
        })

        # Create party
        self.party, = self.Party.create([{
            'name': 'Bruce Wayne',
            'addresses': [('create', [{
                'name': 'Bruce Wayne',
                'party': Eval('id'),
                'city': 'Gotham',
                'country': self.country.id,
                'subdivision': self.subdivision.id,
            }])],
            'account_receivable': self._get_account_by_kind(
                'receivable').id,
            'contact_mechanisms': [('create', [
                {'type': 'mobile', 'value': '8888888888'},
            ])],
        }])

        self.payment_term, = self._create_payment_term()

    def test_0010_test_party_account_statement_report_wizard_case_1(self):
        """
        Test the sales report wizard for amount format 'Cr./Dr.'
        """
        ActionReport = POOL.get('ir.action.report')
        ReportWizard = POOL.get(
            'report.party_account_statement.wizard', type="wizard"
        )
        Move = POOL.get('account.move')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
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

    def test_0015_test_party_account_statement_report_wizard_case_2(self):
        """
        Test the sales report wizard for amount format '+/-'
        """
        ActionReport = POOL.get('ir.action.report')
        ReportWizard = POOL.get(
            'report.party_account_statement.wizard', type="wizard"
        )
        Move = POOL.get('account.move')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
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

    def test_0020_test_party_balance_for_date_case_1(self):
        """
        Test the party balance for the given date
        """
        Move = POOL.get('account.move')
        Invoice = POOL.get('account.invoice')
        InvoiceLine = POOL.get('account.invoice.line')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
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
                    'type': 'out_invoice',
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
                    'invoice_type': 'out_invoice',
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

    def test_0030_test_party_balance_for_date_case_2(self):
        """
        Test the party balance for the given date
        """
        Move = POOL.get('account.move')
        Invoice = POOL.get('account.invoice')
        InvoiceLine = POOL.get('account.invoice.line')

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
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
                    'type': 'out_invoice',
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
                    'invoice_type': 'out_invoice',
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

    def test_0040_test_moves_for_fiscal_year(self):
        """
        Test if the moves returned by query are not limited to present
        fiscal year
        """
        Move = POOL.get('account.move')
        PartyAccountStatement = POOL.get(
            'report.party_account_statement', type="report"
        )

        with Transaction().start(DB_NAME, USER, context=CONTEXT):
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
