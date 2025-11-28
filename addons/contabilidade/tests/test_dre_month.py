from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import date


class TestDREMonth(TransactionCase):

    def test_wizard_month_compute_no_moves(self):
        """Sanity: create a wizard for a specific month and ensure _compute_dre runs and returns structured lines (no exceptions)."""
        Dre = self.env['contabilidade.dre.wizard'].with_user(self.env.uid)
        # choose a month (first day of month)
        period = date(2025, 11, 1)
        wiz = Dre.create({'period': fields.Date.to_string(period), 'show_zero_accounts': True})
        # manually call compute
        wiz._compute_dre()
        # After computing, wizard should have numeric totals and at least the sections created
        self.assertIsNotNone(wiz.total_receita)
        self.assertIsNotNone(wiz.total_despesa)
        # should have lines created (even if zero)
        self.assertTrue(len(wiz.line_ids) >= 1)
        names = [l.name for l in wiz.line_ids]
        # expect the top section 'RECEITAS'
        self.assertIn('RECEITAS', names)
*** End Patch