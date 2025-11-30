from odoo import api, fields, models, Command
from odoo.tools.float_utils import float_is_zero
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

MONTH_SELECTION = [
    ('1', 'Janeiro'),
    ('2', 'Fevereiro'),
    ('3', 'Março'),
    ('4', 'Abril'),
    ('5', 'Maio'),
    ('6', 'Junho'),
    ('7', 'Julho'),
    ('8', 'Agosto'),
    ('9', 'Setembro'),
    ('10', 'Outubro'),
    ('11', 'Novembro'),
    ('12', 'Dezembro'),
]

class ContabilidadeBalancoPatrimonialWizard(models.TransientModel):
    _name = 'contabilidade.balanco.patrimonial.wizard'
    _description = 'Balanço Patrimonial (análise vertical e horizontal)'

    month_recent = fields.Selection(
        selection=MONTH_SELECTION,
        string='Mês 2', required=True, default=lambda self: str(fields.Date.context_today(self).month)
    )
    year_recent = fields.Selection(
        selection=lambda self: self.get_years(),
        string='Ano 2', required=True, default=lambda self: str(fields.Date.context_today(self).year)
    )
    month_previous = fields.Selection(
        selection=MONTH_SELECTION,
        string='Mês 1', required=True, default=lambda self: str((fields.Date.context_today(self) - relativedelta(months=1)).month)
    )
    year_previous = fields.Selection(
        selection=lambda self: self.get_years(),
        string='Ano 1', required=True, default=lambda self: str((fields.Date.context_today(self) - relativedelta(months=1)).year)
    )

    @staticmethod
    def get_years():
        return [(str(i), str(i)) for i in range(2000, 2100)]


    show_zero_accounts        = fields.Boolean(string='Mostrar contas zeradas', default=False)
    currency_id               = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    line_ids                  = fields.One2many('contabilidade.balanco.patrimonial.line', 'wizard_id', string='Lines', readonly=True, compute='_compute_balanco')
    total_ativo_recent        = fields.Monetary(string='Total A Recente', currency_field='currency_id', compute='_compute_balanco')
    total_ativo_previous      = fields.Monetary(string='Total A Anterior', currency_field='currency_id', compute='_compute_balanco')
    total_passivo_pl_recent   = fields.Monetary(string='Total P Recente', currency_field='currency_id', compute='_compute_balanco')
    total_passivo_pl_previous = fields.Monetary(string='Total P Anterior', currency_field='currency_id', compute='_compute_balanco')

    @api.onchange('month_recent', 'year_recent', 'month_previous', 'year_previous', 'show_zero_accounts')
    def _onchange_filters(self):
        self._compute_balanco()

    @api.onchange('month_previous', 'year_previous', 'month_recent', 'year_recent')
    def _onchange_dates(self):
        for wizard in self:
            if (
                wizard.month_previous
                and wizard.year_previous
                and wizard.month_recent
                and wizard.year_recent
                and wizard.month_previous == wizard.month_recent
                and wizard.year_previous == wizard.year_recent
            ):
                return {
                    'warning': {
                        'title': "Meses iguais selecionados",
                        'message': "Mês 1 e Mês 2 estão iguais. A análise horizontal ficará zerada.",
                    }
                }


    def _map_area_from_group(self, grupo_contabil: str) -> str:
        """Map plano de contas group -> área contábil (para sinal)."""
        return {
            'circulante': 'ativo',
            'nao_circulante': 'ativo',
            'passivo_circulante': 'passivo',
            'passivo_nao_circulante': 'passivo',
            'patrimonio': 'patrimonio',
        }.get(grupo_contabil)

    def _compute_natural_balance(self, area: str, debit_sum: float, credit_sum: float) -> float:
        """Saldo com sinal contábil natural."""
        if area == 'ativo':
            return debit_sum - credit_sum
        return credit_sum - debit_sum


    @api.depends('month_recent', 'year_recent', 'month_previous', 'year_previous', 'show_zero_accounts', 'currency_id')
    def _compute_balanco(self):
        Diario = self.env['contabilidade.livro.diario'].sudo()
        Account = self.env['contabilidade.contas'].sudo()

        BS_GROUPS = [
            'circulante', 'nao_circulante',
            'passivo_circulante', 'passivo_nao_circulante',
            'patrimonio',
        ]

        GROUP_INFO = {
            'circulante': {
                'label': 'Ativo Circulante',
                'section': 'ativo',
            },
            'nao_circulante': {
                'label': 'Ativo Não Circulante',
                'section': 'ativo',
            },
            'passivo_circulante': {
                'label': 'Passivo Circulante',
                'section': 'passivo_pl',
            },
            'passivo_nao_circulante': {
                'label': 'Passivo Não Circulante',
                'section': 'passivo_pl',
            },
            'patrimonio': {
                'label': 'Patrimônio Líquido',
                'section': 'passivo_pl',
            },
        }

        for wizard in self:
            wizard.line_ids = [Command.clear()]
            wizard.total_ativo_recent = 0.0
            wizard.total_ativo_previous = 0.0
            wizard.total_passivo_pl_recent = 0.0
            wizard.total_passivo_pl_previous = 0.0

            if not wizard.month_recent or not wizard.year_recent or not wizard.month_previous or not wizard.year_previous:
                continue

            currency = wizard.currency_id
            precision = currency.rounding

            # Converte mês/ano para datas (último dia de cada mês selecionado)
            from datetime import date, timedelta
            base_date_recent = date(int(wizard.year_recent), int(wizard.month_recent), 1)
            base_date_previous = date(int(wizard.year_previous), int(wizard.month_previous), 1)
            date_recent = (base_date_recent + relativedelta(months=1)) - timedelta(days=1)
            date_previous = (base_date_previous + relativedelta(months=1)) - timedelta(days=1)

            # --- movimentos até cada data (posição) ---
            user_field = 'user_id' if 'user_id' in Diario._fields else 'create_uid'
            domain_base = [(user_field, '=', self.env.user.id)]

            moves_recent = Diario.search([
                *domain_base,
                ('data', '<=', date_recent),
            ])
            moves_previous = Diario.search([
                *domain_base,
                ('data', '<=', date_previous),
            ])

            debit_recent = {}
            credit_recent = {}
            debit_previous = {}
            credit_previous = {}

            for m in moves_recent:
                if m.conta_debito_id:
                    debit_recent[m.conta_debito_id.id] = debit_recent.get(m.conta_debito_id.id, 0.0) + (m.valor or 0.0)
                if m.conta_credito_id:
                    credit_recent[m.conta_credito_id.id] = credit_recent.get(m.conta_credito_id.id, 0.0) + (m.valor or 0.0)

            for m in moves_previous:
                if m.conta_debito_id:
                    debit_previous[m.conta_debito_id.id] = debit_previous.get(m.conta_debito_id.id, 0.0) + (m.valor or 0.0)
                if m.conta_credito_id:
                    credit_previous[m.conta_credito_id.id] = credit_previous.get(m.conta_credito_id.id, 0.0) + (m.valor or 0.0)

            # contas de balanço
            accounts = Account.search([
                ('grupo_contabil', 'in', BS_GROUPS),
                '|', '|',
                ('user_id', '=', self.env.user.id),
                ('user_id', '=', False),
                ('user_id', '=', 1),
            ], order='codigo asc, conta asc, id asc')

            # contas de resultado
            receita_accounts = Account.search([
                ('grupo_contabil', 'in', ['receita', 'receitas']),
                '|', '|',
                ('user_id', '=', self.env.user.id),
                ('user_id', '=', False),
                ('user_id', '=', 1),
            ])
            despesa_accounts = Account.search([
                ('grupo_contabil', 'in', ['despesa', 'despesas']),
                '|', '|',
                ('user_id', '=', self.env.user.id),
                ('user_id', '=', False),
                ('user_id', '=', 1),
            ])

            account_data_by_group = {g: [] for g in BS_GROUPS}
            group_totals_recent = {g: 0.0 for g in BS_GROUPS}
            group_totals_previous = {g: 0.0 for g in BS_GROUPS}

            total_ativo_recent = total_ativo_previous = 0.0
            total_passivo_pl_recent = total_passivo_pl_previous = 0.0

            # saldos por conta
            for acc in accounts:
                group_key = acc.grupo_contabil
                area = wizard._map_area_from_group(group_key)
                if not area:
                    continue

                debit_r = debit_recent.get(acc.id, 0.0)
                credit_r = credit_recent.get(acc.id, 0.0)
                debit_p = debit_previous.get(acc.id, 0.0)
                credit_p = credit_previous.get(acc.id, 0.0)

                balance_recent = wizard._compute_natural_balance(area, debit_r, credit_r)
                balance_previous = wizard._compute_natural_balance(area, debit_p, credit_p)

                if (
                    not wizard.show_zero_accounts
                    and float_is_zero(balance_recent, precision_rounding=precision)
                    and float_is_zero(balance_previous, precision_rounding=precision)
                ):
                    continue

                section = GROUP_INFO[group_key]['section']

                if area == 'ativo':
                    total_ativo_recent += balance_recent
                    total_ativo_previous += balance_previous
                else:
                    total_passivo_pl_recent += balance_recent
                    total_passivo_pl_previous += balance_previous

                group_totals_recent[group_key] += balance_recent
                group_totals_previous[group_key] += balance_previous

                account_data_by_group[group_key].append({
                    'account_id': acc.id,
                    'name': acc.name,
                    'group_key': group_key,
                    'section': section,
                    'area': area,
                    'saldo_recent': balance_recent,
                    'saldo_previous': balance_previous,
                })

            # resultado acumulado
            def _net_result(debit_map, credit_map):
                total_receita = sum((credit_map.get(acc.id, 0.0) - debit_map.get(acc.id, 0.0)) for acc in receita_accounts)
                total_despesa = sum((debit_map.get(acc.id, 0.0) - credit_map.get(acc.id, 0.0)) for acc in despesa_accounts)
                return total_receita - total_despesa

            resultado_recent = _net_result(debit_recent, credit_recent)
            resultado_previous = _net_result(debit_previous, credit_previous)

            if not (
                float_is_zero(resultado_recent, precision_rounding=precision)
                and float_is_zero(resultado_previous, precision_rounding=precision)
                and not wizard.show_zero_accounts
            ):
                group_key = 'patrimonio'
                section = 'passivo_pl'

                group_totals_recent[group_key] += resultado_recent
                group_totals_previous[group_key] += resultado_previous
                total_passivo_pl_recent += resultado_recent
                total_passivo_pl_previous += resultado_previous

                account_data_by_group[group_key].append({
                    'account_id': False,
                    'name': 'Lucros/Prejuízos Acumulados',
                    'group_key': group_key,
                    'section': section,
                    'area': 'patrimonio',
                    'saldo_recent': resultado_recent,
                    'saldo_previous': resultado_previous,
                })

            def percent(value, denom):
                if float_is_zero(denom, precision_rounding=precision):
                    return 0.0
                return value / denom

            def ah(recent_val, previous_val):
                if float_is_zero(previous_val, precision_rounding=precision):
                    return False
                return (recent_val - previous_val) / previous_val

            line_commands = []
            seq = 0

            def add_line(values):
                nonlocal seq
                seq += 1
                values.setdefault('sequence', seq)
                values.setdefault('currency_id', currency.id)
                line_commands.append(Command.create(values))

            # HEADER ATIVO
            add_line({
                'name': 'ATIVO',
                'section': 'ativo',
                'display_type': 'section',
                'saldo_recent': currency.round(total_ativo_recent),
                'saldo_previous': currency.round(total_ativo_previous),
                'av_recent': percent(total_ativo_recent, total_ativo_recent),
                'av_previous': percent(total_ativo_previous, total_ativo_previous),
                'ah_percent': ah(total_ativo_recent, total_ativo_previous),
            })

            # grupos de ATIVO (subtotais)
            for group_key in ('circulante', 'nao_circulante'):
                group_label = GROUP_INFO[group_key]['label']
                group_r = group_totals_recent.get(group_key, 0.0)
                group_p = group_totals_previous.get(group_key, 0.0)

                if (
                    not wizard.show_zero_accounts
                    and float_is_zero(group_r, precision_rounding=precision)
                    and float_is_zero(group_p, precision_rounding=precision)
                ):
                    continue

                add_line({
                    'name': group_label,
                    'section': 'ativo',
                    'group_key': group_key,
                    'display_type': 'subtotal',
                    'saldo_recent': currency.round(group_r),
                    'saldo_previous': currency.round(group_p),
                    'av_recent': percent(group_r, total_ativo_recent),
                    'av_previous': percent(group_p, total_ativo_previous),
                    'ah_percent': ah(group_r, group_p),
                })

                for data in account_data_by_group.get(group_key, []):
                    saldo_r = data['saldo_recent']
                    saldo_p = data['saldo_previous']

                    if (
                        not wizard.show_zero_accounts
                        and float_is_zero(saldo_r, precision_rounding=precision)
                        and float_is_zero(saldo_p, precision_rounding=precision)
                    ):
                        continue

                    add_line({
                        'conta_id': data['account_id'],
                        'name': data['name'],
                        'section': 'ativo',
                        'group_key': group_key,
                        'display_type': 'line',
                        'saldo_recent': currency.round(saldo_r),
                        'saldo_previous': currency.round(saldo_p),
                        'av_recent': percent(saldo_r, total_ativo_recent),
                        'av_previous': percent(saldo_p, total_ativo_previous),
                        'ah_percent': ah(saldo_r, saldo_p),
                    })

            # HEADER PASSIVO + PL
            add_line({
                'name': 'PASSIVO + PL',
                'section': 'passivo_pl',
                'display_type': 'section',
                'saldo_recent': currency.round(total_passivo_pl_recent),
                'saldo_previous': currency.round(total_passivo_pl_previous),
                'av_recent': percent(total_passivo_pl_recent, total_passivo_pl_recent),
                'av_previous': percent(total_passivo_pl_previous, total_passivo_pl_previous),
                'ah_percent': ah(total_passivo_pl_recent, total_passivo_pl_previous),
            })

            # grupos de PASSIVO + PL (subtotais)
            for group_key in ('passivo_circulante', 'passivo_nao_circulante', 'patrimonio'):
                group_label = GROUP_INFO[group_key]['label']
                group_r = group_totals_recent.get(group_key, 0.0)
                group_p = group_totals_previous.get(group_key, 0.0)

                if (
                    not wizard.show_zero_accounts
                    and float_is_zero(group_r, precision_rounding=precision)
                    and float_is_zero(group_p, precision_rounding=precision)
                ):
                    continue

                add_line({
                    'name': group_label,
                    'section': 'passivo_pl',
                    'group_key': group_key,
                    'display_type': 'subtotal',
                    'saldo_recent': currency.round(group_r),
                    'saldo_previous': currency.round(group_p),
                    'av_recent': percent(group_r, total_passivo_pl_recent),
                    'av_previous': percent(group_p, total_passivo_pl_previous),
                    'ah_percent': ah(group_r, group_p),
                })

                for data in account_data_by_group.get(group_key, []):
                    saldo_r = data['saldo_recent']
                    saldo_p = data['saldo_previous']

                    if (
                        not wizard.show_zero_accounts
                        and float_is_zero(saldo_r, precision_rounding=precision)
                        and float_is_zero(saldo_p, precision_rounding=precision)
                    ):
                        continue

                    add_line({
                        'conta_id': data['account_id'],
                        'name': data['name'],
                        'section': 'passivo_pl',
                        'group_key': group_key,
                        'display_type': 'line',
                        'saldo_recent': currency.round(saldo_r),
                        'saldo_previous': currency.round(saldo_p),
                        'av_recent': percent(saldo_r, total_passivo_pl_recent),
                        'av_previous': percent(saldo_p, total_passivo_pl_previous),
                        'ah_percent': ah(saldo_r, saldo_p),
                    })

            wizard.line_ids = line_commands
            wizard.total_ativo_recent = currency.round(total_ativo_recent)
            wizard.total_ativo_previous = currency.round(total_ativo_previous)
            wizard.total_passivo_pl_recent = currency.round(total_passivo_pl_recent)
            wizard.total_passivo_pl_previous = currency.round(total_passivo_pl_previous)


class ContabilidadeBalancoPatrimonialLine(models.TransientModel):
    _name = 'contabilidade.balanco.patrimonial.line'
    _description = 'Linha do Balanço Patrimonial (AV/AH)'
    _order = 'section, sequence, id'

    wizard_id      = fields.Many2one('contabilidade.balanco.patrimonial.wizard', ondelete='cascade')
    sequence       = fields.Integer(default=10)
    section        = fields.Selection([('ativo', 'Ativo'),('passivo_pl', 'Passivo + PL')], string='Section', required=True, index=True)
    display_type   = fields.Selection([('line', 'Line'),('section', 'Section header'),('subtotal', 'Subtotal')], string='Display Type', default='line')
    conta_id       = fields.Many2one('contabilidade.contas', string='Account')
    name           = fields.Char(string='Conta', required=True)
    user_id        = fields.Many2one('res.users', string='Usuário', default=lambda self: self.env.user)
    currency_id    = fields.Many2one('res.currency', string='Currency', required=True)
    saldo_recent   = fields.Monetary(string='Valor Mês 2', currency_field='currency_id')
    saldo_previous = fields.Monetary(string='Valor Mês 1', currency_field='currency_id')
    av_recent      = fields.Float(string='AV% Mês 2')
    av_previous    = fields.Float(string='AV% Mês 1')
    ah_percent     = fields.Float(string='AH%')
    codigo         = fields.Char(string='Code', related='conta_id.codigo', store=False)
    grupo_contabil = fields.Selection(string='Grupo Contábil', related='conta_id.grupo_contabil', store=False)
    group_key      = fields.Selection([
        ('circulante', 'Ativo Circulante'),
        ('nao_circulante', 'Ativo Não Circulante'),
        ('passivo_circulante', 'Passivo Circulante'),
        ('passivo_nao_circulante', 'Passivo Não Circulante'),
        ('patrimonio', 'Patrimônio Líquido'),
    ], string='Tipo')

