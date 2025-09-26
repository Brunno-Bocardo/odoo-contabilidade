from odoo import api, fields, models, _
from odoo import Command

class ContabilidadeBalancoPatrimonialWizard(models.TransientModel):
    _name = 'contabilidade.balanco.patrimonial.wizard'
    _description = 'Balanço Patrimonial (consulta)'