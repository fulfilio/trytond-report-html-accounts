# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import urllib
from itertools import tee, izip
from trytond.pool import Pool, PoolMeta
from trytond.protocols.jsonrpc import JSONEncoder, json
from sql.aggregate import Sum
from trytond.transaction import Transaction

from openlabs_report_webkit import ReportWebkit

__metaclass__ = PoolMeta
__all__ = ['AccountMoveLine']


class AccountMoveLine:
    'Account Move Line'
    __name__ = 'account.move.line'

    def origin_details(self):
        """
        Returns the origin as a string to print on checks
        """
        Model = Pool().get('ir.model')

        try:
            self.origin.rec_name
        except AttributeError:
            return None

        model, = Model.search([
            ('model', '=', self.origin.__name__)
        ])
        return "%s, %s" % (model.name, self.origin.rec_name)


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


class AgedBalance(ReportWebkit):
    __name__ = 'account.aged_balance'

    @classmethod
    def parse(cls, report, objects, data, localcontext):
        pool = Pool()
        Party = pool.get('party.party')
        MoveLine = pool.get('account.move.line')
        Move = pool.get('account.move')
        Account = pool.get('account.account')
        Company = pool.get('company.company')
        Date = pool.get('ir.date')
        cursor = Transaction().connection.cursor()

        line = MoveLine.__table__()
        move = Move.__table__()
        account = Account.__table__()

        company = Company(data['company'])
        localcontext['digits'] = company.currency.digits
        localcontext['posted'] = data['posted']
        with Transaction().set_context(context=localcontext):
            line_query, _ = MoveLine.query_get(line)

        def get_current_by_party(today):
            """
            Not Due Yet + Without Maturity date
            """
            term_query = line.maturity_date == None
            term_query |= line.maturity_date > today
            cursor.execute(
                *line.join(
                    move, condition=line.move == move.id
                ).join(
                    account, condition=line.account == account.id
                ).select(
                    line.party, Sum(line.debit) - Sum(line.credit),
                    where=(line.party != None) &
                    account.active &
                    account.kind.in_(kind) &
                    (line.reconciliation == None) &
                    (account.company == data['company']) &
                    term_query &
                    line_query,
                    group_by=line.party,
                    having=(Sum(line.debit) - Sum(line.credit)) != 0)
            )
            return cursor.fetchall()

        def get_balance_by_party(to_date, from_date):
            term_query = line.maturity_date <= to_date
            term_query &= line.maturity_date > from_date
            cursor.execute(
                *line.join(
                    move, condition=line.move == move.id
                ).join(
                    account, condition=line.account == account.id
                ).select(
                    line.party, Sum(line.debit) - Sum(line.credit),
                    where=(line.party != None) &
                    account.active &
                    account.kind.in_(kind) &
                    (line.reconciliation == None) &
                    (account.company == data['company']) &
                    term_query &
                    line_query,
                    group_by=line.party,
                    having=(Sum(line.debit) - Sum(line.credit)) != 0)
            )
            return cursor.fetchall()

        terms = (data['term1'], data['term2'], data['term3'])
        if data['unit'] == 'month':
            coef = timedelta(days=30)
        else:
            coef = timedelta(days=1)

        today = Date.today()
        dates = [
            today,
            today - data['term1'] * coef,     # 0-term1
            today - data['term2'] * coef,     # term1-term2
            today - data['term3'] * coef,     # term2-term3
            datetime.min,                       # older
        ]

        kind = {
            'both': ('payable', 'receivable'),
            'supplier': ('payable',),
            'customer': ('receivable',),
        }[data['balance_type']]

        res = defaultdict(lambda: defaultdict(lambda: Decimal('0')))
        totals = defaultdict(lambda: Decimal('0'))
        for position, date_range in enumerate(pairwise(dates)):
            term = ['term1', 'term2', 'term3', 'older'][position]
            for party, balance in get_balance_by_party(*date_range):
                res[party][term] = balance
                totals[term] += balance

        for party, balance in get_current_by_party(today):
            res[party]['current'] = balance
            totals['current'] += balance

        for party in Party.browse(res.keys()):
            res[party.id]['total'] = party.receivable + party.payable
            totals['net'] += res[party.id]['total']

        def get_balance_url(party, term=None):
            "Given a party and term number (1-3) or older return URI"
            path = MoveLine.__url__
            domain = [
                ('reconciliation', '=', None),
                ('party', '=', party.id),
                ('account.kind', 'in', kind),
            ]
            if data['posted']:
                domain.append(('move.state', '=', 'posted'))

            if term == 'current':
                domain.append([
                    'OR', [
                        ('maturity_date', '>', today),
                    ], [
                        ('maturity_date', '=', None),
                    ],
                ])

            elif term is not None:
                # Add the date range
                term_index = 4 if term == 'older' else term
                to_date, from_date = dates[term_index - 1], dates[term_index]
                domain.extend([
                    ('maturity_date', '<=', to_date),
                    ('maturity_date', '>', from_date),
                ])
            return ';'.join((
                path,
                urllib.urlencode([
                    ('domain', json.dumps(domain, cls=JSONEncoder))
                ])
            ))

        localcontext['parties'] = Party.search([('id', 'in', res.keys())])
        localcontext['balances'] = res
        localcontext['totals'] = totals
        localcontext['kind'] = kind
        localcontext['terms'] = terms
        localcontext['unit'] = data['unit']
        localcontext['report'] = report
        localcontext['currency_code'] = company.currency.code
        localcontext['get_balance_url'] = get_balance_url

        return super(AgedBalance, cls).parse(
            report, objects, data, localcontext
        )
