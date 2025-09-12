from odoo import models, fields

class ContabilidadeLivroDiario(models.Model):
    _name = "contabilidade.livro.diario"
    _description = "Contabilidade Livro Diário"

    nome = fields.Char(string="Livro Diário", required=True)
