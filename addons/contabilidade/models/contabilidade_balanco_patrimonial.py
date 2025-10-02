from odoo import api, fields, models, Command
from odoo.tools.float_utils import float_is_zero

class ContabilidadeBalancoPatrimonialWizard(models.TransientModel):
    _name = 'contabilidade.balanco.patrimonial.wizard'
    _description = 'Balanço Patrimonial (consulta)'

    data_base = fields.Date(
        string='Data-base',
        required=True,
        default=lambda self: fields.Date.context_today(self)
    )
    show_zero_accounts = fields.Boolean(string='Exibir contas zeradas', default=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.BRL'))

    ativo_line_ids = fields.One2many(
        'contabilidade.balanco.patrimonial.line', 'wizard_ativo_id',
        string='Contas Ativo', compute='_compute_balanco', readonly=True,
    )
    passivo_line_ids = fields.One2many(
        'contabilidade.balanco.patrimonial.line', 'wizard_passivo_id',
        string='Contas Passivo', compute='_compute_balanco', readonly=True,
    )
    patrimonio_line_ids = fields.One2many(
        'contabilidade.balanco.patrimonial.line', 'wizard_patrimonio_id',
        string='Contas Patrimônio Líquido', compute='_compute_balanco', readonly=True,
    )

    total_ativo = fields.Monetary(string='Total Ativo', currency_field='currency_id', compute='_compute_balanco')
    total_passivo = fields.Monetary(string='Total Passivo', currency_field='currency_id', compute='_compute_balanco')
    total_patrimonio = fields.Monetary(string='Total Patrimônio Líquido', currency_field='currency_id', compute='_compute_balanco')
    total_passivo_patrimonio = fields.Monetary(string='Total Passivo + PL', currency_field='currency_id', compute='_compute_balanco')

    @api.onchange('data_base', 'show_zero_accounts')
    def _onchange_filters(self):
        self._compute_balanco()

    def _map_area_from_group(self, grupo_contabil: str) -> str:
        return {
            'circulante': 'ativo',
            'nao_circulante': 'ativo',
            'passivo_circulante': 'passivo',
            'passivo_nao_circulante': 'passivo',
            'patrimonio': 'patrimonio',
        }.get(grupo_contabil)

    def _compute_natural_balance(self, area: str, debit_sum: float, credit_sum: float) -> float:
        return (debit_sum - credit_sum) if area == 'ativo' else (credit_sum - debit_sum)

    @api.depends('data_base', 'show_zero_accounts', 'currency_id')
    def _compute_balanco(self):
        Diario = self.env['contabilidade.livro.diario'].sudo()
        Account = self.env['contabilidade.contas'].sudo()

        bs_groups = [
            'circulante', 'nao_circulante',
            'passivo_circulante', 'passivo_nao_circulante',
            'patrimonio',
        ]

        for wizard in self:
            wizard.ativo_line_ids = [Command.clear()]
            wizard.passivo_line_ids = [Command.clear()]
            wizard.patrimonio_line_ids = [Command.clear()]

            total_ativo = total_passivo = total_patrimonio = 0.0

            if not wizard.data_base:
                wizard.total_ativo = wizard.total_passivo = wizard.total_patrimonio = 0.0
                continue

            currency = wizard.currency_id
            movimentos = Diario.search([('data', '<=', wizard.data_base)])

            # soma débitos/créditos por conta
            debit_by_acc = {}
            credit_by_acc = {}
            for m in movimentos:
                if m.conta_debito_id:
                    debit_by_acc[m.conta_debito_id.id] = debit_by_acc.get(m.conta_debito_id.id, 0.0) + (m.valor or 0.0)
                if m.conta_credito_id:
                    credit_by_acc[m.conta_credito_id.id] = credit_by_acc.get(m.conta_credito_id.id, 0.0) + (m.valor or 0.0)

            accounts = Account.search([
                ('grupo_contabil', 'in', bs_groups),
                '|', '|',
                    ('user_id', '=', self.env.user.id),
                    ('user_id', '=', False),
                    ('user_id', '=', 1)
            ], order='codigo asc, conta asc, id asc')

            area_inverse = {
                'ativo': 'wizard_ativo_id',
                'passivo': 'wizard_passivo_id',
                'patrimonio': 'wizard_patrimonio_id',
            }
            lines_by_area = {'ativo': [], 'passivo': [], 'patrimonio': []}

            for acc in accounts:
                area = wizard._map_area_from_group(acc.grupo_contabil)
                if not area:
                    continue

                debit_sum = debit_by_acc.get(acc.id, 0.0)
                credit_sum = credit_by_acc.get(acc.id, 0.0)
                balance = wizard._compute_natural_balance(area, debit_sum, credit_sum)

                if not wizard.show_zero_accounts and float_is_zero(balance, precision_rounding=currency.rounding):
                    continue
                
                # Accumulate totals
                if area == 'ativo':
                    total_ativo += balance
                elif area == 'passivo':
                    total_passivo += balance
                elif area == 'patrimonio':
                    total_patrimonio += balance

                vals = {
                    'conta_id': acc.id,
                    'nome': acc.name, 
                    'area': area,
                    'saldo': currency.round(balance),
                    'currency_id': currency.id,
                }
                vals[area_inverse[area]] = wizard.id
                lines_by_area[area].append(Command.create(vals))

            # === Receitas - Despesas ===
            receita_accounts = Account.search([('grupo_contabil', '=', 'receitas')])
            despesa_accounts = Account.search([('grupo_contabil', '=', 'despesa')])

            total_receita = sum(
                credit_by_acc.get(acc.id, 0.0) - debit_by_acc.get(acc.id, 0.0)
                for acc in receita_accounts
            )
            total_despesa = sum(
                debit_by_acc.get(acc.id, 0.0) - credit_by_acc.get(acc.id, 0.0)
                for acc in despesa_accounts
            )

            resultado_acumulado = total_receita - total_despesa

            # Procurar contas de Lucro/Prejuízo Acumulado no PL
            lucro_account = Account.search([
                ('grupo_contabil', '=', 'patrimonio'),
                ('conta', 'ilike', 'lucro acumul')
            ], limit=1)
            prej_account = Account.search([
                ('grupo_contabil', '=', 'patrimonio'),
                ('conta', 'ilike', 'preju')
            ], limit=1)

            # fallback por códigos conhecidos (se nomes não batem)
            if not lucro_account:
                lucro_account = Account.search([('codigo', 'in', ['5.0.1', '4.0.1', '5.0.1'])], limit=1)
            if not prej_account:
                prej_account = Account.search([('codigo', 'in', ['5.0.2', '4.0.2'])], limit=1)

            if not float_is_zero(resultado_acumulado, precision_rounding=currency.rounding):
                if resultado_acumulado > 0:
                    # Mostrar Lucro Acumulado
                    lines_by_area['patrimonio'].append(Command.create({
                        'conta_id': lucro_account.id if lucro_account else False,
                        'nome': lucro_account.conta if lucro_account else "Lucros Acumulados",
                        'area': 'patrimonio',
                        'saldo': currency.round(resultado_acumulado),
                        'currency_id': currency.id,
                    }))
                    total_patrimonio += resultado_acumulado
                else:
                    # Mostrar Prejuízo Acumulado
                    val = abs(resultado_acumulado)
                    lines_by_area['patrimonio'].append(Command.create({
                        'conta_id': prej_account.id if prej_account else False,
                        'nome': prej_account.conta if prej_account else "Prejuízos Acumulados",
                        'area': 'patrimonio',
                        'saldo': currency.round(-val) if False else currency.round(-val), 
                        'currency_id': currency.id,
                    }))
                    total_patrimonio += resultado_acumulado

            wizard.ativo_line_ids = lines_by_area['ativo']
            wizard.passivo_line_ids = lines_by_area['passivo']
            wizard.patrimonio_line_ids = lines_by_area['patrimonio']

            # Totais finais
            wizard.total_ativo = currency.round(total_ativo)
            wizard.total_passivo = currency.round(total_passivo)
            wizard.total_patrimonio = currency.round(total_patrimonio)
            wizard.total_passivo_patrimonio = currency.round(total_passivo + total_patrimonio)
 


class ContabilidadeBalancoPatrimonialLine(models.TransientModel):
    _name = 'contabilidade.balanco.patrimonial.line'
    _description = 'Linha do Balanço Patrimonial (consulta)'
    _order = 'area, id'

    wizard_ativo_id = fields.Many2one('contabilidade.balanco.patrimonial.wizard', ondelete='cascade')
    wizard_passivo_id = fields.Many2one('contabilidade.balanco.patrimonial.wizard', ondelete='cascade')
    wizard_patrimonio_id = fields.Many2one('contabilidade.balanco.patrimonial.wizard', ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Usuário", default=lambda self: self.env.user)

    conta_id = fields.Many2one('contabilidade.contas', string='Conta', index=True)
    area = fields.Selection([
        ('ativo', 'Ativo'),
        ('passivo', 'Passivo'),
        ('patrimonio', 'Patrimônio Líquido'),
    ], string='Área', required=True, index=True)

    saldo = fields.Monetary(string='Saldo', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moeda', required=True)

    codigo = fields.Char(string='Código', related='conta_id.codigo', store=False)
    grupo_contabil = fields.Selection(string='Grupo Contábil', related='conta_id.grupo_contabil', store=False)
    nome = fields.Char(string="Conta")