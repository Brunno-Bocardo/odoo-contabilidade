from odoo import models, fields

class ContabilidadeContas(models.Model):
    _name = "contabilidade.contas"
    _description = "Contabilidade Contas"

    nome = fields.Char(string="Conta", required=True)
    codigo = fields.Char(string="Código", required=True)
    nome_codigo = fields.Char(string="Conta + Código", required=True)

    grupo_contabil = fields.Selection([
        ('ativo', 'Ativo'),
        ('passivo', 'Passivo'),
        ('patrimonio', 'Patrimônio Líquido'),
        ('despesa', 'Despesa'),
        ('apuracao', 'Apuração do Resultado'),
    ], string="Grupo Contábil", required=True)

    subgrupo1 = fields.Selection([
        ('circulante', 'Ativo Circulante'),
        ('nao_circulante', 'Ativo Não Circulante'),
        ('passivo_circulante', 'Passivo Circulante'),
        ('passivo_nao_circulante', 'Passivo Não Circulante'),
    ], string="Subgrupo 1")

    subgrupo2 = fields.Selection([
        ('realizavel', 'Realizável a longo Prazo'),
        ('investimentos', 'Investimentos'),
        ('imobilizado', 'Imobilizado'),
        ('intangivel', 'Intangível'),
    ], string="Subgrupo 2")


    def create(self, vals):
        vals['nome_codigo'] = f"{vals.get('codigo')} - {vals.get('nome')}"
        return super(ContabilidadeContas, self).create(vals)
    
    def write(self, vals):
        if 'codigo' in vals or 'nome' in vals:
            vals['nome_codigo'] = f"{vals.get('codigo')} - {vals.get('nome')}"
        return super(ContabilidadeContas, self).write(vals)
