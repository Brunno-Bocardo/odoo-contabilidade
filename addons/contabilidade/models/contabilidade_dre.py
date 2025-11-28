from odoo import api, fields, models, Command
import datetime
import calendar


class ContabilidadeDreWizard(models.TransientModel):
    _name = 'contabilidade.dre.wizard'
    _description = 'Demonstração do Resultado do Exercício (DRE) - Wizard'

    period = fields.Date(
        string='Período (mês)',
        required=True,
        default=lambda self: fields.Date.to_string(datetime.date.today().replace(day=1)),
    )
    show_zero_accounts = fields.Boolean(string='Mostrar contas zeradas', default=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)

    line_ids = fields.One2many('contabilidade.dre.line', 'wizard_id', string='Linhas', readonly=True, compute='_compute_dre')

    total_receita = fields.Monetary(string='Total Receitas', currency_field='currency_id', compute='_compute_dre')
    total_despesa = fields.Monetary(string='Total Despesas', currency_field='currency_id', compute='_compute_dre')
    lucro_prejuizo = fields.Monetary(string='Lucro/Prejuízo', currency_field='currency_id', compute='_compute_dre')

    receita_bruta = fields.Monetary(string='Receita Bruta', currency_field='currency_id', compute='_compute_dre')
    impostos_sobre_venda = fields.Monetary(string='Impostos sobre Venda', currency_field='currency_id', compute='_compute_dre')
    devolucoes = fields.Monetary(string='Devoluções', currency_field='currency_id', compute='_compute_dre')
    receita_liquida = fields.Monetary(string='Receita Líquida', currency_field='currency_id', compute='_compute_dre')

    custo_inicial = fields.Monetary(string='Custo Inicial', currency_field='currency_id', compute='_compute_dre')
    custo_atual = fields.Monetary(string='Custo Atual', currency_field='currency_id', compute='_compute_dre')
    lucro_bruto = fields.Monetary(string='Lucro Bruto', currency_field='currency_id', compute='_compute_dre')

    despesas_operacionais = fields.Monetary(string='Despesas Operacionais', currency_field='currency_id', compute='_compute_dre')

    resultado_antes_financeiro = fields.Monetary(string='Resultado antes das Receitas/Despesas Financeiras', currency_field='currency_id', compute='_compute_dre')

    receita_financeira = fields.Monetary(string='Receita Financeira', currency_field='currency_id', compute='_compute_dre')
    despesa_financeira = fields.Monetary(string='Despesa Financeira', currency_field='currency_id', compute='_compute_dre')

    lucro_liquido = fields.Monetary(string='Lucro Líquido', currency_field='currency_id', compute='_compute_dre')

    @api.onchange('period', 'show_zero_accounts')
    def _onchange_filters(self):
        self._compute_dre()
        return None

    @api.depends('period', 'show_zero_accounts', 'currency_id')
    def _compute_dre(self):
        Diario = self.env['contabilidade.livro.diario'].sudo()
        Account = self.env['contabilidade.contas'].sudo()

        for wiz in self:
            wiz.line_ids = [Command.clear()]

            wiz.total_receita = 0.0
            wiz.total_despesa = 0.0
            wiz.lucro_prejuizo = 0.0
            wiz.receita_bruta = 0.0
            wiz.impostos_sobre_venda = 0.0
            wiz.devolucoes = 0.0
            wiz.receita_liquida = 0.0
            wiz.custo_inicial = 0.0
            wiz.custo_atual = 0.0
            wiz.lucro_bruto = 0.0
            wiz.despesas_operacionais = 0.0
            wiz.resultado_antes_financeiro = 0.0
            wiz.receita_financeira = 0.0
            wiz.despesa_financeira = 0.0
            wiz.lucro_liquido = 0.0

            if not wiz.period:
                continue

            # Turn the period selected (first-day date) into start and end date of that month
            try:
                per = fields.Date.from_string(wiz.period)
            except Exception:
                per = None
            if not per:
                continue
            date_from = per.replace(day=1)
            last_day = calendar.monthrange(per.year, per.month)[1]
            date_to = per.replace(day=last_day)

            user_field = 'user_id' if 'user_id' in Diario._fields else 'create_uid'
            domain_base = [(user_field, '=', self.env.user.id)]

            moves = Diario.search([
                *domain_base,
                ('data', '>=', date_from),
                ('data', '<=', date_to),
            ])

            moves_before = Diario.search([
                *domain_base,
                ('data', '<', date_from),
            ])

            debit_map = {}
            credit_map = {}
            debit_map_before = {}
            credit_map_before = {}

            for m in moves:
                if m.conta_debito_id:
                    debit_map[m.conta_debito_id.id] = debit_map.get(m.conta_debito_id.id, 0.0) + (m.valor or 0.0)
                if m.conta_credito_id:
                    credit_map[m.conta_credito_id.id] = credit_map.get(m.conta_credito_id.id, 0.0) + (m.valor or 0.0)

            for m in moves_before:
                if m.conta_debito_id:
                    debit_map_before[m.conta_debito_id.id] = debit_map_before.get(m.conta_debito_id.id, 0.0) + (m.valor or 0.0)
                if m.conta_credito_id:
                    credit_map_before[m.conta_credito_id.id] = credit_map_before.get(m.conta_credito_id.id, 0.0) + (m.valor or 0.0)

            receita_accounts = Account.search([
                ('grupo_contabil', 'in', ['receita', 'receitas']),
                '|', '|',
                ('user_id', '=', self.env.user.id),
                ('user_id', '=', False),
                ('user_id', '=', 1),
            ], order='codigo asc, conta asc, id asc')

            despesa_accounts = Account.search([
                ('grupo_contabil', 'in', ['despesa', 'despesas']),
                '|', '|',
                ('user_id', '=', self.env.user.id),
                ('user_id', '=', False),
                ('user_id', '=', 1),
            ], order='codigo asc, conta asc, id asc')

            total_receita = 0.0
            total_despesa = 0.0

            for acc in receita_accounts:
                total_receita += (credit_map.get(acc.id, 0.0) - debit_map.get(acc.id, 0.0))

            for acc in despesa_accounts:
                total_despesa += (debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0))

            wiz.total_receita = wiz.currency_id.round(total_receita)
            wiz.total_despesa = wiz.currency_id.round(total_despesa)
            wiz.lucro_prejuizo = wiz.currency_id.round(total_receita - total_despesa)

            receita_bruta_val = sum(credit_map.get(acc.id, 0.0) for acc in receita_accounts)

            imposto_accounts = Account.search([('conta', 'ilike', 'impost')])
            impostos_val = sum(credit_map.get(acc.id, 0.0) - debit_map.get(acc.id, 0.0) for acc in imposto_accounts)

            devolucao_accounts = Account.search([('conta', 'ilike', 'devol')])
            devolucoes_val = sum(debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0) for acc in devolucao_accounts)

            cogs_accounts = (
                Account.search([('conta', 'ilike', 'cmv')])
                + Account.search([('conta', 'ilike', 'cpv')])
                + Account.search([('conta', 'ilike', 'csv')])
            )
            custo_inicial_val = sum(debit_map_before.get(acc.id, 0.0) - credit_map_before.get(acc.id, 0.0) for acc in cogs_accounts)
            custo_atual_val = sum(debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0) for acc in cogs_accounts)

            receita_financeira_accounts = Account.search([('conta', 'ilike', 'receita financ')]) + Account.search([('conta', 'ilike', 'receita financeira')])
            despesa_financeira_accounts = Account.search([('conta', 'ilike', 'despesa financ')]) + Account.search([('conta', 'ilike', 'despesa financeira')])

            receita_financeira_val = sum(credit_map.get(acc.id, 0.0) - debit_map.get(acc.id, 0.0) for acc in receita_financeira_accounts)
            despesa_financeira_val = sum(debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0) for acc in despesa_financeira_accounts)

            all_despesa_accounts = despesa_accounts
            despesas_operacionais_accounts = [a for a in all_despesa_accounts if a.id not in [x.id for x in cogs_accounts + despesa_financeira_accounts]]
            despesas_operacionais_val = sum(debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0) for acc in despesas_operacionais_accounts)

            wiz.receita_bruta = wiz.currency_id.round(receita_bruta_val)
            wiz.impostos_sobre_venda = wiz.currency_id.round(impostos_val)
            wiz.devolucoes = wiz.currency_id.round(devolucoes_val)
            wiz.receita_liquida = wiz.currency_id.round((receita_bruta_val or 0.0) - (impostos_val or 0.0) - (devolucoes_val or 0.0))

            wiz.custo_inicial = wiz.currency_id.round(custo_inicial_val)
            wiz.custo_atual = wiz.currency_id.round(custo_atual_val)
            wiz.lucro_bruto = wiz.currency_id.round((wiz.receita_liquida or 0.0) - (custo_atual_val or 0.0))

            wiz.despesas_operacionais = wiz.currency_id.round(despesas_operacionais_val)

            wiz.resultado_antes_financeiro = wiz.currency_id.round((wiz.lucro_bruto or 0.0) - (despesas_operacionais_val or 0.0))

            wiz.receita_financeira = wiz.currency_id.round(receita_financeira_val)
            wiz.despesa_financeira = wiz.currency_id.round(despesa_financeira_val)

            wiz.lucro_liquido = wiz.currency_id.round((wiz.resultado_antes_financeiro or 0.0) + (wiz.receita_financeira or 0.0) - (wiz.despesa_financeira or 0.0))

            seq = 0
            line_cmds = []

            def add(values):
                nonlocal seq
                seq += 1
                values.setdefault('sequence', seq)
                values.setdefault('currency_id', wiz.currency_id.id)
                line_cmds.append(Command.create(values))


            # 1) RECEITAS (exibe detalhes e total líquido)
            add({'name': 'RECEITAS', 'display_type': 'section', 'valor': wiz.receita_liquida})

            # show receita_bruta, impostos, devoluções and receita_liquida breakdown
            add({'name': 'Receita Bruta', 'display_type': 'line', 'valor': wiz.receita_bruta})
            add({'name': '(-) Impostos sobre Venda', 'display_type': 'line', 'valor': -wiz.impostos_sobre_venda})
            add({'name': '(-) Devoluções', 'display_type': 'line', 'valor': -wiz.devolucoes})
            add({'name': 'TOTAL - Receita Líquida', 'display_type': 'subtotal', 'valor': wiz.receita_liquida})

            # 2) CUSTOS (CMV/CPV/CSV) -> Lucro Bruto
            add({'name': '(-) CUSTOS (CMV / CPV / CSV)', 'display_type': 'section', 'valor': -wiz.custo_atual})
            for acc in cogs_accounts:
                val = debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0)
                if not wiz.show_zero_accounts and abs(val) < 1e-12:
                    continue
                add({
                    'conta_id': acc.id,
                    'name': acc.name,
                    'display_type': 'line',
                    'valor': wiz.currency_id.round(-val),
                })
            add({'name': 'TOTAL CUSTOS', 'display_type': 'subtotal', 'valor': -wiz.custo_atual})

            # Lucro Bruto = Receita Líquida - Custos
            add({'name': 'LUCRO BRUTO', 'display_type': 'section', 'valor': wiz.lucro_bruto})

            # 3) DESPESAS OPERACIONAIS -> Resultado antes financeiro
            add({'name': '(-) DESPESAS OPERACIONAIS', 'display_type': 'section', 'valor': -wiz.despesas_operacionais})
            for acc in despesas_operacionais_accounts:
                val = debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0)
                if not wiz.show_zero_accounts and abs(val) < 1e-12:
                    continue
                add({
                    'conta_id': acc.id,
                    'name': acc.name,
                    'display_type': 'line',
                    'valor': wiz.currency_id.round(-val),
                })
            add({'name': 'TOTAL DESPESAS OPERACIONAIS', 'display_type': 'subtotal', 'valor': -wiz.despesas_operacionais})

            # Resultado antes das receitas/despesas financeiras
            add({'name': 'RESULTADO ANTES FINANCEIRO', 'display_type': 'section', 'valor': wiz.resultado_antes_financeiro})

            # 4) RESULTADOS FINANCEIROS
            if receita_financeira_accounts:
                add({'name': 'RECEITA FINANCEIRA', 'display_type': 'section', 'valor': wiz.receita_financeira})
                for acc in receita_financeira_accounts:
                    val = credit_map.get(acc.id, 0.0) - debit_map.get(acc.id, 0.0)
                    if not wiz.show_zero_accounts and abs(val) < 1e-12:
                        continue
                    add({
                        'conta_id': acc.id,
                        'name': acc.name,
                        'display_type': 'line',
                        'valor': wiz.currency_id.round(val),
                    })

            if despesa_financeira_accounts:
                add({'name': 'DESPESA FINANCEIRA', 'display_type': 'section', 'valor': -wiz.despesa_financeira})
                for acc in despesa_financeira_accounts:
                    val = debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0)
                    if not wiz.show_zero_accounts and abs(val) < 1e-12:
                        continue
                    add({
                        'conta_id': acc.id,
                        'name': acc.name,
                        'display_type': 'line',
                        'valor': wiz.currency_id.round(-val),
                    })

            # 5) LUCRO LÍQUIDO final
            add({'name': 'LUCRO LÍQUIDO', 'display_type': 'section', 'valor': wiz.lucro_liquido})

            wiz.line_ids = line_cmds


class ContabilidadeDreLine(models.TransientModel):
    _name = 'contabilidade.dre.line'
    _description = 'Linha da DRE'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('contabilidade.dre.wizard', ondelete='cascade')
    sequence = fields.Integer(default=10)
    display_type = fields.Selection([('line', 'Line'), ('section', 'Section header'), ('subtotal', 'Subtotal')], default='line')
    conta_id = fields.Many2one('contabilidade.contas', string='Conta')
    name = fields.Char(string='Descrição', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    valor = fields.Monetary(string='Valor', currency_field='currency_id')
    av_percent = fields.Float(string='Percentual sobre Receitas')
    codigo = fields.Char(string='Código', related='conta_id.codigo', store=False)
    grupo_contabil = fields.Selection(string='Grupo Contábil', related='conta_id.grupo_contabil', store=False)
