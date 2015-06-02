# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from report_html_accounts import PartyAccountStatementReport, \
    GeneratePartyAccountStatementReportStart, \
    GeneratePartyAccountStatementReport, Party
from account import AccountMoveLine


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
        module='report_html_accounts', type_='report'
    )
