# -*- coding: utf-8 -*-
from report_html_accounts import ReportMixin

from trytond.pool import PoolMeta

__metaclass__ = PoolMeta
__all__ = ['InvoiceHTMLReport']


class InvoiceHTMLReport(ReportMixin):
    __name__ = 'account.invoice.html'

    @classmethod
    def get_jinja_filters(cls):
        rv = super(InvoiceHTMLReport, cls).get_jinja_filters()
        rv['product_lines'] = lambda lines: filter(
            lambda l: l.type == 'line' and l not in (
                l.invoice.account_management_fee_line, l.invoice.shipping_line),
            lines
        )
        rv['sorted_tax_lines'] = lambda lines: sorted(
            lines, key=lambda l: l.tax.rate
        )
        return rv
