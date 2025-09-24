from odoo import models, fields

class ContabilidadeContas(models.Model):
    _name = "contabilidade.contas"
    _description = "Contabilidade Contas"

    name = fields.Char(string="Conta + Código", required=True)
    conta = fields.Char(string="Conta", required=True)
    codigo = fields.Char(string="Código", readonly=True)
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

    # TODO: Modificar no campo form para ficar escrito Subgrupo.
    subgrupo1 = fields.Selection([
        ('realizavel', 'Realizável a longo Prazo'),
        ('investimentos', 'Investimentos'),
        ('imobilizado', 'Imobilizado'),
        ('intangivel', 'Intangível'),
    ], string="Subgrupo 1")


    # Lógica de escrever o código automaticamente
    def create(self, vals):
        if not vals.get('codigo') and vals.get('grupo_contabil'):
            prefixos = {
                'circulante': '1',
                'nao_circulante': '2',
                'passivo_circulante': '3',
                'passivo_nao_circulante': '4',
                'patrimonio': '5',
                'despesa': '6',
                'apuracao': '6',
                'receitas': '7',
            }
            prefixo = prefixos[vals['grupo_contabil']]

            subgrupo_map = {
                'realizavel': '0',
                'investimentos': '1',
                'imobilizado': '2',
                'intangivel': '3',
            }

            if vals['grupo_contabil'] == 'nao_circulante':
                subgrupo1 = vals.get('subgrupo1')
                if not subgrupo1:
                    raise ValueError("Selecione um subgrupo para Ativo Não Circulante.")
                digito_meio = subgrupo_map[subgrupo]

                ultima = self.search([
                    ('grupo_contabil', '=', 'nao_circulante'),
                    ('subgrupo1', '=', subgrupo1)
                ], order='codigo desc', limit=1)

                if ultima and ultima.codigo:
                    partes = ultima.codigo.split('.')
                    partes[-1] = str(int(partes[-1]) + 1)
                    novo_codigo = '.'.join(partes)
                else:
                    novo_codigo = f"{prefixo}.{digito_meio}.1"

            else:
                ultima = self.search([('grupo_contabil', '=', vals['grupo_contabil'])], order='codigo desc', limit=1)
                if ultima and ultima.codigo:
                    partes = ultima.codigo.split('.')
                    partes[-1] = str(int(partes[-1]) + 1)
                    novo_codigo = '.'.join(partes)
                else:
                    novo_codigo = f"{prefixo}.0.1"

            vals['codigo'] = novo_codigo

        conta_nome = vals.get('conta', '')
        codigo_val = vals.get('codigo', '')
        vals['name'] = f"{codigo_val} - {conta_nome}" if conta_nome else codigo_val

        return super(ContabilidadeContas, self).create(vals)

    def write(self, vals):
        if 'codigo' in vals or 'conta' in vals:
            conta_nome = vals.get('conta', self.conta)
            codigo_val = vals.get('codigo', self.codigo)
            vals['name'] = f"{codigo_val} - {conta_nome}" if conta_nome else codigo_val
        return super(ContabilidadeContas, self).write(vals)

    # def create(self, vals):
    #     vals['name'] = f"{vals.get('codigo')} - {vals.get('conta')}"
    #     return super(ContabilidadeContas, self).create(vals)
    
    # def write(self, vals):
    #     if 'codigo' in vals or 'conta' in vals:
    #         vals['name'] = f"{vals.get('codigo')} - {vals.get('conta')}"
    #     return super(ContabilidadeContas, self).write(vals)
