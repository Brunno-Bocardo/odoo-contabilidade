from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


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


class ContabilidadeIndicadoresWizard(models.TransientModel):
    _name = 'contabilidade.indicadores.wizard'
    _description = 'Indicadores Financeiros (liquidez e retorno)'

    # -------------------------------------------------------------------------
    # Context / filters
    # -------------------------------------------------------------------------
    month = fields.Selection(
        selection=MONTH_SELECTION,
        string='Mês',
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month),
        help="Mês utilizado para calcular a posição de balanço e os índices "
             "de liquidez. O sistema usa o último dia do mês selecionado "
             "como data de corte.",
    )
    year = fields.Selection(
        selection=lambda self: self._get_years(),
        string='Ano',
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year),
        help="Ano utilizado em conjunto com o mês para determinar a data de corte.",
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moeda',
        required=True,
        default=lambda self: self.env.ref('base.BRL'),
        help="Moeda utilizada para exibição dos valores monetários.",
    )

    @staticmethod
    def _get_years():
        return [(str(i), str(i)) for i in range(2000, 2100)]

    # -------------------------------------------------------------------------
    # Liquidity ratios - numerators/denominators
    # -------------------------------------------------------------------------
    # Liquidez Imediata
    liq_imediata_disponivel = fields.Monetary(
        string='Disponível (Caixa e Equivalentes)',
        compute='_compute_indicators',
    )
    liq_imediata_passivo_circ = fields.Monetary(
        string='Passivo Circulante',
        compute='_compute_indicators',
    )
    liq_imediata = fields.Float(
        string='Liquidez Imediata',
        digits=(16, 4),
        compute='_compute_indicators',
    )

    # Liquidez Seca
    liq_seca_ativo_sem_estoque = fields.Monetary(
        string='Ativo Circulante - Estoques',
        
        compute='_compute_indicators',
    )
    liq_seca_passivo_circ = fields.Monetary(
        string='Passivo Circulante (Seca)',
        
        compute='_compute_indicators',
    )
    liq_seca = fields.Float(
        string='Liquidez Seca',
        digits=(16, 4),
        compute='_compute_indicators',
    )

    # Liquidez Corrente
    liq_corrente_ativo_circ = fields.Monetary(
        string='Ativo Circulante',
        
        compute='_compute_indicators',
    )
    liq_corrente_passivo_circ = fields.Monetary(
        string='Passivo Circulante (Corrente)',
        
        compute='_compute_indicators',
    )
    liq_corrente = fields.Float(
        string='Liquidez Corrente',
        digits=(16, 4),
        compute='_compute_indicators',
    )

    # Liquidez Geral
    liq_geral_ativo_circ_rlp = fields.Monetary(
        string='Ativo Circulante + RLP',
        
        compute='_compute_indicators',
    )
    liq_geral_passivo_total = fields.Monetary(
        string='Passivo Total (Exigível)',
        
        compute='_compute_indicators',
    )
    liq_geral = fields.Float(
        string='Liquidez Geral',
        digits=(16, 4),
        compute='_compute_indicators',
    )

    # Solvência Geral
    solvencia_ativo_total = fields.Monetary(
        string='Ativo Total',
        
        compute='_compute_indicators',
    )
    solvencia_passivo_total = fields.Monetary(
        string='Passivo Total (Exigível)',
        
        compute='_compute_indicators',
    )
    solvencia_geral = fields.Float(
        string='Solvência Geral',
        digits=(16, 4),
        compute='_compute_indicators',
    )

    # -------------------------------------------------------------------------
    # Return ratios - ROA and ROE (net income + bases)
    # -------------------------------------------------------------------------
    roa_net_income = fields.Monetary(
        string='Lucro Líquido (Período)',
        
        compute='_compute_indicators',
        help="Lucro líquido do período, do início do ano até o fim do mês selecionado.",
    )
    roa_total_assets = fields.Monetary(
        string='Ativo Total (base ROA)',
        
        compute='_compute_indicators',
    )
    roa = fields.Float(
        string='ROA',
        digits=(16, 4),
        compute='_compute_indicators',
        help="Return on Assets = Lucro Líquido / Ativo Total.",
    )

    roe_net_income = fields.Monetary(
        string='Lucro Líquido (Período, ROE)',
        
        compute='_compute_indicators',
    )
    roe_equity = fields.Monetary(
        string='Patrimônio Líquido (base ROE)',
        
        compute='_compute_indicators',
    )
    roe = fields.Float(
        string='ROE',
        digits=(16, 4),
        compute='_compute_indicators',
        help="Return on Equity = Lucro Líquido / Patrimônio Líquido.",
    )

    # -------------------------------------------------------------------------
    # ROI - user enters gain and cost, system computes percentage
    # -------------------------------------------------------------------------
    roi_gain = fields.Monetary(
        string='Ganho do Investimento',
        
        help="Ganho do investimento/projeto (preenchido manualmente).",
    )
    roi_investment_cost = fields.Monetary(
        string='Custo do Investimento',
        
        help="Valor total investido no projeto/investimento.",
    )
    roi = fields.Float(
        string='ROI',
        digits=(16, 4),
        compute='_compute_roi',
        help="Return on Investment = Ganho / Custo do Investimento.",
    )

    # -------------------------------------------------------------------------
    # Core compute: liquidity + ROA/ROE
    # -------------------------------------------------------------------------
    @api.depends('month', 'year', 'currency_id')
    def _compute_indicators(self):
        Diario = self.env['contabilidade.livro.diario'].sudo()
        Account = self.env['contabilidade.contas'].sudo()

        BS_GROUPS = [
            'circulante',
            'nao_circulante',
            'passivo_circulante',
            'passivo_nao_circulante',
            'patrimonio',
        ]

        for wizard in self:
            currency = wizard.currency_id or self.env.company.currency_id
            precision = currency.rounding or 0.01

            # Initialize all computed fields so Odoo is always satisfied
            wizard.liq_imediata_disponivel = 0.0
            wizard.liq_imediata_passivo_circ = 0.0
            wizard.liq_imediata = 0.0

            wizard.liq_seca_ativo_sem_estoque = 0.0
            wizard.liq_seca_passivo_circ = 0.0
            wizard.liq_seca = 0.0

            wizard.liq_corrente_ativo_circ = 0.0
            wizard.liq_corrente_passivo_circ = 0.0
            wizard.liq_corrente = 0.0

            wizard.liq_geral_ativo_circ_rlp = 0.0
            wizard.liq_geral_passivo_total = 0.0
            wizard.liq_geral = 0.0

            wizard.solvencia_ativo_total = 0.0
            wizard.solvencia_passivo_total = 0.0
            wizard.solvencia_geral = 0.0

            wizard.roa_net_income = 0.0
            wizard.roa_total_assets = 0.0
            wizard.roa = 0.0

            wizard.roe_net_income = 0.0
            wizard.roe_equity = 0.0
            wizard.roe = 0.0

            if not wizard.month or not wizard.year:
                # Nothing to compute without month/year
                continue

            # Build cutoff date as the last day of the selected month
            base_date = date(int(wizard.year), int(wizard.month), 1)
            date_cutoff = (base_date + relativedelta(months=1)) - timedelta(days=1)

            # Helper for safe ratios
            def _ratio(num, denom):
                if float_is_zero(denom, precision_rounding=precision):
                    return 0.0
                return num / denom

            # -----------------------------------------------------------------
            # Build debit/credit maps for balance sheet position (<= cutoff)
            # -----------------------------------------------------------------
            user_field = 'user_id' if 'user_id' in Diario._fields else 'create_uid'
            domain_base = [(user_field, '=', self.env.user.id)]

            moves_bs = Diario.search([
                *domain_base,
                ('data', '<=', date_cutoff),
            ])

            debit_bs = {}
            credit_bs = {}
            for move in moves_bs:
                if move.conta_debito_id:
                    debit_bs[move.conta_debito_id.id] = debit_bs.get(move.conta_debito_id.id, 0.0) + (move.valor or 0.0)
                if move.conta_credito_id:
                    credit_bs[move.conta_credito_id.id] = credit_bs.get(move.conta_credito_id.id, 0.0) + (move.valor or 0.0)

            # All balance sheet accounts (same grouping idea as your Balanço)
            balance_accounts = Account.search([
                ('grupo_contabil', 'in', BS_GROUPS),
                '|', '|',
                ('user_id', '=', self.env.user.id),
                ('user_id', '=', False),
                ('user_id', '=', 1),
            ])

            # Revenue and expense accounts – used for net income (ROA/ROE)
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

            # -----------------------------------------------------------------
            # Net income for the period (Lucro Líquido)
            # Period: from beginning of year to cutoff date (DRE-style)
            # -----------------------------------------------------------------
            year_start = date(date_cutoff.year, 1, 1)

            moves_dre = Diario.search([
                *domain_base,
                ('data', '>=', year_start),
                ('data', '<=', date_cutoff),
            ])

            debit_dre = {}
            credit_dre = {}
            for move in moves_dre:
                if move.conta_debito_id:
                    debit_dre[move.conta_debito_id.id] = debit_dre.get(move.conta_debito_id.id, 0.0) + (move.valor or 0.0)
                if move.conta_credito_id:
                    credit_dre[move.conta_credito_id.id] = credit_dre.get(move.conta_credito_id.id, 0.0) + (move.valor or 0.0)

            total_receita = sum(
                (credit_dre.get(acc.id, 0.0) - debit_dre.get(acc.id, 0.0))
                for acc in receita_accounts
            )
            total_despesa = sum(
                (debit_dre.get(acc.id, 0.0) - credit_dre.get(acc.id, 0.0))
                for acc in despesa_accounts
            )
            net_income = total_receita - total_despesa

            wizard.roa_net_income = currency.round(net_income)
            wizard.roe_net_income = wizard.roa_net_income

            # -----------------------------------------------------------------
            # Walk through balance accounts once and aggregate everything
            # -----------------------------------------------------------------
            def _natural_balance(acc, debit, credit):
                """Compute natural balance by group (assets vs liabilities)."""
                group = acc.grupo_contabil
                if group in ('circulante', 'nao_circulante'):
                    # Assets: debit - credit
                    return (debit or 0.0) - (credit or 0.0)
                elif group in ('passivo_circulante', 'passivo_nao_circulante', 'patrimonio'):
                    # Liabilities & equity: credit - debit
                    return (credit or 0.0) - (debit or 0.0)
                # fallback
                return (debit or 0.0) - (credit or 0.0)

            total_ativo_circ = 0.0
            total_ativo_nao_circ = 0.0
            total_passivo_circ = 0.0
            total_passivo_nao_circ = 0.0
            total_patrimonio = 0.0

            total_disponivel = 0.0       # cash, banks, equivalents
            total_estoque = 0.0          # inventory
            total_rlp = 0.0              # realizable long-term

            for acc in balance_accounts:
                debit_val = debit_bs.get(acc.id, 0.0)
                credit_val = credit_bs.get(acc.id, 0.0)
                balance = _natural_balance(acc, debit_val, credit_val)

                group = acc.grupo_contabil
                name_lower = (acc.conta or '').lower()

                if group == 'circulante':
                    total_ativo_circ += balance

                    # "Disponível": basic heuristic based on account name
                    if any(token in name_lower for token in ['caixa', 'banco', 'disponi', 'aplic']):
                        total_disponivel += balance

                    # Inventory accounts (Estoque)
                    if any(token in name_lower for token in ['estoque', 'mercadoria']):
                        total_estoque += balance

                elif group == 'nao_circulante':
                    total_ativo_nao_circ += balance

                    # Long-term receivables (RLP)
                    if getattr(acc, 'subgrupo1', False) == 'realizavel':
                        total_rlp += balance

                elif group == 'passivo_circulante':
                    total_passivo_circ += balance

                elif group == 'passivo_nao_circulante':
                    total_passivo_nao_circ += balance

                elif group == 'patrimonio':
                    total_patrimonio += balance

            total_ativo = total_ativo_circ + total_ativo_nao_circ
            total_passivo_exigivel = total_passivo_circ + total_passivo_nao_circ

            # -----------------------------------------------------------------
            # Liquidity ratios (following spreadsheet structure)
            # -----------------------------------------------------------------
            # Liquidez Imediata: Disponível / Passivo Circulante
            wizard.liq_imediata_disponivel = currency.round(total_disponivel)
            wizard.liq_imediata_passivo_circ = currency.round(total_passivo_circ)
            wizard.liq_imediata = _ratio(total_disponivel, total_passivo_circ)

            # Liquidez Seca: (Ativo Circulante - Estoque) / Passivo Circulante
            ativo_sem_estoque = total_ativo_circ - total_estoque
            wizard.liq_seca_ativo_sem_estoque = currency.round(ativo_sem_estoque)
            wizard.liq_seca_passivo_circ = currency.round(total_passivo_circ)
            wizard.liq_seca = _ratio(ativo_sem_estoque, total_passivo_circ)

            # Liquidez Corrente: Ativo Circulante / Passivo Circulante
            wizard.liq_corrente_ativo_circ = currency.round(total_ativo_circ)
            wizard.liq_corrente_passivo_circ = currency.round(total_passivo_circ)
            wizard.liq_corrente = _ratio(total_ativo_circ, total_passivo_circ)

            # Liquidez Geral: (Ativo Circulante + RLP) / (Passivo Circulante + Passivo Não Circulante)
            ativo_circ_rlp = total_ativo_circ + total_rlp
            wizard.liq_geral_ativo_circ_rlp = currency.round(ativo_circ_rlp)
            wizard.liq_geral_passivo_total = currency.round(total_passivo_exigivel)
            wizard.liq_geral = _ratio(ativo_circ_rlp, total_passivo_exigivel)

            # Solvência Geral: Ativo Total / (Passivo Circulante + Passivo Não Circulante)
            wizard.solvencia_ativo_total = currency.round(total_ativo)
            wizard.solvencia_passivo_total = currency.round(total_passivo_exigivel)
            wizard.solvencia_geral = _ratio(total_ativo, total_passivo_exigivel)

            # -----------------------------------------------------------------
            # ROA and ROE
            # -----------------------------------------------------------------
            # ROA: Net Income / Total Assets
            wizard.roa_total_assets = currency.round(total_ativo)
            wizard.roa = _ratio(net_income, total_ativo)

            # ROE: Net Income / Equity
            wizard.roe_equity = currency.round(total_patrimonio)
            wizard.roe = _ratio(net_income, total_patrimonio)

    # -------------------------------------------------------------------------
    # ROI: depends only on user-entered gain/cost
    # -------------------------------------------------------------------------
    @api.depends('roi_gain', 'roi_investment_cost', 'currency_id')
    def _compute_roi(self):
        for wizard in self:
            currency = wizard.currency_id or self.env.company.currency_id
            precision = currency.rounding or 0.01

            roi_value = 0.0
            if not float_is_zero(wizard.roi_investment_cost, precision_rounding=precision):
                roi_value = wizard.roi_gain / wizard.roi_investment_cost

            wizard.roi = roi_value
