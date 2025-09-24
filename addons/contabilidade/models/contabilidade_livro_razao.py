from odoo import api, fields, models, _
from odoo import Command

class ContabilidadeLivroRazaoWizard(models.TransientModel):
    _name = 'contabilidade.livro.razao.wizard'
    _description = 'Livro Razão (consulta)'

    conta_id = fields.Many2one('contabilidade.contas', string='Conta', required=True)
    currency_id = fields.Many2one('res.currency',  default=lambda self: self.env.ref('base.BRL'), required=True)

    saldo_inicial = fields.Monetary(string='Saldo Inicial', currency_field='currency_id', compute='_compute_totais')
    total_debito  = fields.Monetary(string='Total Débitos', currency_field='currency_id', compute='_compute_totais')
    total_credito = fields.Monetary(string='Total Créditos', currency_field='currency_id', compute='_compute_totais')
    saldo_final   = fields.Char(string='Saldo Final', compute='_compute_totais')

    line_ids = fields.One2many('contabilidade.livro.razao.line', 'wizard_id', string='Lançamentos', compute='_compute_lines', readonly=True)



    # Atualiza automaticamente ao mudar filtros
    @api.onchange('conta_id')
    def onchange_filters(self):
        self._compute_lines()
        self._compute_totais()


    def _get_domain_movimentos(self):
        """Retorna o domínio para buscar lançamentos do livro diário relacionados à conta selecionada no wizard."""
        self.ensure_one()
        if not self.conta_id:
            return [('id', '=', 0)]
        return [
            '|',
            ('conta_credito_id', '=', self.conta_id.id),
            ('conta_debito_id', '=', self.conta_id.id),
        ]


    def _compute_lines(self):
        """Monta as linhas do livro razão a partir do Livro Diário."""
        Diario = self.env['contabilidade.livro.diario']

        for wizard in self:
            wizard.line_ids = [Command.clear()]
            if not wizard.conta_id:
                continue

            movimentos = Diario.search(
                wizard._get_domain_movimentos(),
                order='data asc, id asc'
            )

            linhas_razao = []
            for movimento in movimentos:
                linhas_razao.append(Command.create({
                    'data': movimento.data,
                    'descricao': movimento.descricao,
                    'diario_id': movimento.id,
                    'conta_debito_id': movimento.conta_debito_id.id,
                    'conta_credito_id': movimento.conta_credito_id.id,
                    'debito': movimento.valor if movimento.conta_debito_id.id == wizard.conta_id.id else 0.0,
                    'credito': movimento.valor if movimento.conta_credito_id.id == wizard.conta_id.id else 0.0,
                    'currency_id': wizard.currency_id.id,
                }))

            wizard.line_ids = linhas_razao


    def _compute_totais(self):
        """Calcula saldo inicial, totais e saldo final do razão."""
        Diario = self.env['contabilidade.livro.diario']

        for wizard in self:
            if not wizard.conta_id:
                wizard.saldo_inicial = wizard.total_debito = wizard.total_credito = 0.0
                continue

            conta = wizard.conta_id.id
            saldo_inicial = 0.0
            total_debitos = total_creditos = 0.0

            movimentos = Diario.search(wizard._get_domain_movimentos())
            for movimento in movimentos:
                if movimento.conta_debito_id.id == conta:
                    total_debitos += movimento.valor
                if movimento.conta_credito_id.id == conta:
                    total_creditos += movimento.valor

            if wizard.total_debito >= wizard.total_credito:
                tipo_saldo_final = "C"
            else:
                tipo_saldo_final = "D"

            wizard.saldo_inicial = saldo_inicial
            wizard.total_debito = total_debitos
            wizard.total_credito = total_creditos
            saldo_final_valor = saldo_inicial + total_debitos - total_creditos
            valor_formatado = f"{saldo_final_valor:,.2f}"
            wizard.saldo_final = f"R$ {valor_formatado} {tipo_saldo_final}"



class ContabilidadeLivroRazaoLine(models.TransientModel):
    _name = 'contabilidade.livro.razao.line'
    _description = 'Linha do Livro Razão (consulta)'

    wizard_id = fields.Many2one('contabilidade.livro.razao.wizard', ondelete='cascade')
    data = fields.Date(string='Data')
    descricao = fields.Char(string='Descrição')
    diario_id = fields.Many2one('contabilidade.livro.diario', string='Lançamento')
    conta_debito_id  = fields.Many2one('contabilidade.contas', string='Débito')
    conta_credito_id = fields.Many2one('contabilidade.contas', string='Crédito')
    debito  = fields.Monetary(currency_field='currency_id', string='Débito')
    credito = fields.Monetary(currency_field='currency_id', string='Crédito')
    currency_id = fields.Many2one('res.currency', string='Moeda')
