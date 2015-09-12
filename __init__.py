# -*- coding: utf-8 -*-
from trytond.pool import Pool
from report_html_accounts import PartyAccountStatementReport, \
    GeneratePartyAccountStatementReportStart, \
    GeneratePartyAccountStatementReport, Party
from account import AccountMoveLine, AgedBalance
from invoice import InvoiceHTMLReport


def register():
    Pool.register(
        module='report_html_accounts', type_='model'
    )
    Pool.register(
        GeneratePartyAccountStatementReportStart,
        AccountMoveLine,
        Party,
        module='report_html_accounts', type_='model'
    )
    Pool.register(
        GeneratePartyAccountStatementReport,
        module='report_html_accounts', type_='wizard'
    )
    Pool.register(
        PartyAccountStatementReport,
        InvoiceHTMLReport,
        AgedBalance,
        module='report_html_accounts', type_='report'
    )
