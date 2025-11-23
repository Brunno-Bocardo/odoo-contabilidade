from odoo import api, fields, models, _
from odoo import Command


class ContabilidadeLivroRazaoWizard(models.TransientModel):
    _name = 'contabilidade.livro.razao.wizard'
    _description = 'Livro Razão (consulta)'

    conta_id = fields.Many2one('contabilidade.contas', string='Conta', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.BRL'), required=True)
    saldo_inicial = fields.Char(string='Saldo Inicial', compute='_compute_totais')
    total_debito = fields.Monetary(string='Total Débitos', currency_field='currency_id', compute='_compute_totais')
    total_credito = fields.Monetary(string='Total Créditos', currency_field='currency_id', compute='_compute_totais')
    saldo_final = fields.Char(string='Saldo Final', compute='_compute_totais')
    line_ids = fields.One2many('contabilidade.livro.razao.line', 'wizard_id', string='Lançamentos', compute='_compute_lines', readonly=True,)
    data_base = fields.Date(string='Data Base')

    # Recalcula ao mudar conta OU data
    @api.onchange('conta_id', 'data_base')
    def onchange_filters(self):
        self._compute_lines()
        self._compute_totais()

    def _get_domain_movimentos(self):
        """Domínio base para buscar lançamentos da conta selecionada."""
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

            domain = wizard._get_domain_movimentos()
            # filtra lançamentos >= data_base, se informada
            if wizard.data_base:
                domain = list(domain) + [('data', '>=', wizard.data_base)]

            movimentos = Diario.search(domain, order='data asc, id asc')

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
                wizard.saldo_inicial = ''
                wizard.total_debito = 0.0
                wizard.total_credito = 0.0
                wizard.saldo_final = ''
                continue

            conta_id = wizard.conta_id.id
            base_domain = wizard._get_domain_movimentos()

            # 1) Domínios: abertura (< data_base) e período (>= data_base)
            domain_open = list(base_domain)
            domain_period = list(base_domain)

            if wizard.data_base:
                domain_open.append(('data', '<', wizard.data_base))
                domain_period.append(('data', '>=', wizard.data_base))

            movimentos_abertura = Diario.search(domain_open)
            movimentos_periodo = Diario.search(domain_period)

            def _accumulate(movs):
                debitos = 0.0
                creditos = 0.0
                for movimento in movs:
                    if movimento.conta_debito_id.id == conta_id:
                        debitos += movimento.valor
                    if movimento.conta_credito_id.id == conta_id:
                        creditos += movimento.valor
                return debitos, creditos

            deb_abertura, cred_abertura = _accumulate(movimentos_abertura)
            saldo_inicial_valor = deb_abertura - cred_abertura

            deb_periodo, cred_periodo = _accumulate(movimentos_periodo)
            wizard.total_debito = deb_periodo
            wizard.total_credito = cred_periodo
            saldo_final_valor = saldo_inicial_valor + (deb_periodo - cred_periodo)

            if saldo_inicial_valor > 0:
                tipo_saldo_inicial = "D"
            elif saldo_inicial_valor < 0:
                tipo_saldo_inicial = "C"
            else:
                tipo_saldo_inicial = ""

            valor_inicial_formatado = f"{abs(saldo_inicial_valor):,.2f}"
            wizard.saldo_inicial = f"R$ {valor_inicial_formatado} {tipo_saldo_inicial}".strip()

            # Saldo final
            if saldo_final_valor > 0:
                tipo_saldo_final = "D"
            elif saldo_final_valor < 0:
                tipo_saldo_final = "C"
            else:
                tipo_saldo_final = ""

            valor_final_formatado = f"{abs(saldo_final_valor):,.2f}"
            wizard.saldo_final = f"R$ {valor_final_formatado} {tipo_saldo_final}".strip()


class ContabilidadeLivroRazaoLine(models.TransientModel):
    _name = 'contabilidade.livro.razao.line'
    _description = 'Linha do Livro Razão (consulta)'

    wizard_id = fields.Many2one('contabilidade.livro.razao.wizard', ondelete='cascade')
    data = fields.Date(string='Data')
    descricao = fields.Char(string='Descrição')
    diario_id = fields.Many2one('contabilidade.livro.diario', string='Lançamento')
    conta_debito_id = fields.Many2one('contabilidade.contas', string='Débito')
    conta_credito_id = fields.Many2one('contabilidade.contas', string='Crédito')
    debito = fields.Monetary(currency_field='currency_id', string='Débito')
    credito = fields.Monetary(currency_field='currency_id', string='Crédito')
    currency_id = fields.Many2one('res.currency', string='Moeda')
