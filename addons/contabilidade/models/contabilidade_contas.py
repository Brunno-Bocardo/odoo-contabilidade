from odoo import models, fields

class ContabilidadeContas(models.Model):
    _name = "contabilidade.contas"
    _description = "Contabilidade Contas"

    name = fields.Char(string="Conta + Código", required=True)
    conta = fields.Char(string="Conta", required=True)
    codigo = fields.Char(string="Código", required=True)
    descricao = fields.Text(string="Descrição")

    grupo_contabil = fields.Selection([
        ('circulante', 'Ativo Circulante'),
        ('nao_circulante', 'Ativo Não Circulante'),
        ('passivo_circulante', 'Passivo Circulante'),
        ('passivo_nao_circulante', 'Passivo Não Circulante'),
        ('patrimonio', 'Patrimônio Líquido'),
        ('despesa', 'Despesa'),
        ('apuracao', 'Apuração do Resultado'),
        ('receitas', 'Receitas'),
        
    ], string="Grupo Contábil", required=True)

    subgrupo1 = fields.Selection([
        ('realizavel', 'Realizável a longo Prazo'),
        ('investimentos', 'Investimentos'),
        ('imobilizado', 'Imobilizado'),
        ('intangivel', 'Intangível'),
    ], string="Subgrupo 1")


    # TODO: Incluir a lógica de escrever o código automaticamente

    def create(self, vals):
        vals['name'] = f"{vals.get('codigo')} - {vals.get('conta')}"
        return super(ContabilidadeContas, self).create(vals)
    
    def write(self, vals):
        if 'codigo' in vals or 'conta' in vals:
            vals['name'] = f"{vals.get('codigo')} - {vals.get('conta')}"
        return super(ContabilidadeContas, self).write(vals)
