# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, ModuleTestCase
from trytond.transaction import Transaction
from trytond.pyson import Eval


class BaseTestCase(ModuleTestCase):
    '''
    Base Test Case for report_html_accounts module.
    '''
    module = 'report_html_accounts'

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('report_html_accounts')

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

        Transaction().context.update(
            self.User.get_preferences(context_only=True))

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
