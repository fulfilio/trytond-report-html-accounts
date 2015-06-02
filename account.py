# -*- coding: utf-8 -*-
"""
    account.py
    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool, PoolMeta

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

        if not self.origin:
            return None

        model, = Model.search([
            ('model', '=', self.origin.__name__)
        ])
        return "%s, %s" % (model.name, self.origin.rec_name)
