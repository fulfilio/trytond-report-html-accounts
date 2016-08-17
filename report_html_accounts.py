# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sql.aggregate import Sum
from sql.conditionals import Coalesce

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateAction, StateView, Button
from trytond.exceptions import UserError

from openlabs_report_webkit import ReportWebkit

_ZERO = Decimal('0.0')
__all__ = [
    'PartyAccountStatementReport', 'GeneratePartyAccountStatementReportStart',
    'GeneratePartyAccountStatementReport', 'Party'
]
__metaclass__ = PoolMeta


class ReportMixin(ReportWebkit):
    """
    Mixin Class to inherit from, for all HTML reports.
    """

    @classmethod
    def wkhtml_to_pdf(cls, data, options=None):
        """
        Call wkhtmltopdf to convert the html to pdf
        """
        Company = Pool().get('company.company')

        company = ''
        if Transaction().context.get('company'):
            company = Company(Transaction().context.get('company')).party.name
        options = {
            'margin-bottom': '0.50in',
            'margin-left': '0.50in',
            'margin-right': '0.50in',
            'margin-top': '0.50in',
            'footer-font-size': '8',
            'footer-left': company,
            'footer-line': '',
            'footer-right': '[page]/[toPage]',
            'footer-spacing': '5',
            'page-size': 'Letter',
        }
        return super(ReportMixin, cls).wkhtml_to_pdf(
            data, options=options
        )


class PartyAccountStatementReport(ReportMixin):
    """
    Party Account Statement Report
    """
    __name__ = 'report.party_account_statement'

    @classmethod
    def get_context(cls, records, data):
        MoveLine = Pool().get('account.move.line')
        Party = Pool().get('party.party')
        User = Pool().get('res.user')

        report_context = super(PartyAccountStatementReport, cls).get_context(
            records, data
        )

        if not data['party_id']:
            raise UserError(
                "Please select a party to generate the statement for"
            )
        party = Party(data['party_id'])
        user = User(Transaction().user)
        cursor = Transaction().connection.cursor()

        query, tables = party._get_balance_query(
            data['end_date'], data['start_date'], data['hide_reconciled_lines']
        )
        line = tables['account.move.line']
        move = tables['account.move']
        query.columns += (
            line.id,
        )
        query.order_by = move.date.asc

        cursor.execute(*query)

        move_lines = MoveLine.browse(
            [id[0] for id in cursor.fetchall()]
        )

        report_context.update({
            'move_lines': move_lines,
            'party': party,
            'relativedelta': lambda *args, **kargs: relativedelta(
                *args, **kargs),
            'company': user.company,
            'consider_maturity_date': data['consider_maturity_date'],
            'get_move_lines_maturing':
                lambda *args, **kargs: cls.get_move_lines_maturing(
                    *args, **kargs),
        })
        return report_context

    @classmethod
    def get_move_lines_maturing(cls, party, start_date, end_date):
        """
        Returns the move lines maturing in the given date range
        """
        AccountMoveLines = Pool().get('account.move.line')
        AccountMove = Pool().get('account.move')
        User = Pool().get('res.user')
        Account = Pool().get('account.account')

        user = User(Transaction().user)
        cursor = Transaction().connection.cursor()

        line = AccountMoveLines.__table__()
        move = AccountMove.__table__()
        account = Account.__table__()

        line_query, _ = AccountMoveLines.query_get(line)

        sub_query = line.join(
            account,
            condition=account.id == line.account
        )
        query = sub_query.join(
            move,
            condition=line.move == move.id,
        ).select(
            line.id,
            where=account.active &
            (line.party == party.id) &
            (account.company == user.company.id) &
            (account.kind.in_(('receivable', 'payable'))) &
            (line.maturity_date >= start_date) &
            (line.maturity_date <= end_date) &
            line_query,
            order_by=move.date.asc
        )
        cursor.execute(*query)

        move_line_ids = [id[0] for id in cursor.fetchall()]
        move_lines = AccountMoveLines.browse(move_line_ids)
        return move_lines


class GeneratePartyAccountStatementReportStart(ModelView):
    'Generate Party Account Statement Report'
    __name__ = 'report.party_account_statement.wizard.start'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    consider_maturity_date = fields.Boolean('Consider Maturity Date?')
    hide_reconciled_lines = fields.Boolean('Hide Reconciled Lines?')
    amount_format = fields.Selection([
        ('cr/dr', 'Cr./Dr.'),
        ('+/-', '+/-'),
    ], 'Amount Format')

    @staticmethod
    def default_start_date():
        Date = Pool().get('ir.date')

        # Set first day of current month as the default for start date
        today = Date.today()
        return date(today.year, today.month, 1)

    @staticmethod
    def default_end_date():
        Date = Pool().get('ir.date')

        return Date.today()

    @staticmethod
    def default_consider_maturity_date():
        return False

    @staticmethod
    def default_amount_format():
        return 'cr/dr'


class GeneratePartyAccountStatementReport(Wizard):
    'Generate Party Account Statement Report Wizard'
    __name__ = 'report.party_account_statement.wizard'

    start = StateView(
        'report.party_account_statement.wizard.start',
        'report_html_accounts.report_party_account_statement_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
        ]
    )
    generate = StateAction(
        'report_html_accounts.report_party_account_statement'
    )

    def do_generate(self, action):
        """
        Return report action and the data to pass to it
        """
        data = {
            'party_id': Transaction().context.get('active_id'),
            'start_date': self.start.start_date,
            'end_date': self.start.end_date,
            'consider_maturity_date': self.start.consider_maturity_date,
            'hide_reconciled_lines': self.start.hide_reconciled_lines,
            'amount_format': self.start.amount_format,
        }
        return action, data

    def transition_generate(self):
        return 'end'


class Party:
    __name__ = 'party.party'

    def _get_balance_query(self, end_date,
                           start_date=None, unreconciled_lines_only=True):
        """
        Returns a python-sql object that can be used to query the move tables.
        Does not select anything in the query and leaves it to the programmer
        calling this api.
        """
        MoveLine = Pool().get('account.move.line')
        Account = Pool().get('account.account')
        Move = Pool().get('account.move')
        User = Pool().get('res.user')

        line = MoveLine.__table__()
        account = Account.__table__()
        move = Move.__table__()

        user_id = Transaction().user
        if user_id == 0 and 'user' in Transaction().context:
            user_id = Transaction().context['user']
        user = User(user_id)
        if not user.company:
            return _ZERO
        company_id = user.company.id

        line_query, _ = MoveLine.query_get(line)

        date_where = (move.date <= end_date)
        if start_date is not None:
            date_where &= (move.date >= start_date)

        tables = {
            'account.move.line': line,
            'account.account': account,
            'account.move': move,
        }

        query = line.join(
            account,
            condition=account.id == line.account
        ).join(
            move,
            condition=line.move == move.id
        ).select(
            where=account.active &
            (account.kind.in_(('receivable', 'payable'))) &
            (line.party == self.id) &
            (account.company == company_id) &
            line_query &
            date_where
        )
        if unreconciled_lines_only:
            query.where &= (line.reconciliation == None)  # noqa
        return query, tables

    def get_balance_on(self, date):
        """
        Returns the balance for the party

        :param date: The date for which balance has to be calculated
        """
        cursor = Transaction().connection.cursor()

        query, tables = self._get_balance_query(date)
        line = tables['account.move.line']
        query.columns += (
            Sum(Coalesce(line.debit, 0) - Coalesce(line.credit, 0)),
        )
        cursor.execute(*query)

        _sum, = cursor.fetchall()[0]

        # SQLite uses float for SUM
        if not isinstance(sum, Decimal):
            _sum = _sum and Decimal(str(_sum)) or _ZERO
        return _sum

    def get_opening_balance_on(self, date):
        """
        Returns the balance of party one day before date
        """
        return self.get_balance_on(date - relativedelta(days=1))
