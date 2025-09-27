from odoo import models, fields

class ContabilidadeLivroDiario(models.Model):
    _name = "contabilidade.livro.diario"
    _description = "Contabilidade Livro Diário"

    data = fields.Date(string="Data", required=True)
    descricao = fields.Char(string="Descrição", required=True)
    conta_credito_id = fields.Many2one('contabilidade.contas', string="Crédito", required=True)
    conta_debito_id = fields.Many2one('contabilidade.contas', string="Débito", required=True)
    valor = fields.Float(string="Valor", required=True)
    currency_id = fields.Many2one('res.currency', string="Moeda", default=lambda self: self.env.ref('base.BRL'), required=True)


    def action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "contabilidade.livro.diario",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }