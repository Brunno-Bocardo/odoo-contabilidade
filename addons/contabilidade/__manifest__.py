{
    'name': 'Contabilidade',
    'description': 'Módulo para a aula de contabilidade',
    'version': '17.0',
    
    'depends': [
        'base',
        'web_responsive',
        'muk_web_appsbar',
        'muk_web_colors',
        # 'web_favicon'
    ],
    "assets": {
        "web.assets_backend": [
            # "contabilidade/static/src/scss/dark_theme.scss",
            # 'contabilidade/static/src/xml/favicon.xml',
            # 'contabilidade/static/src/img/logo1.ico',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/contabilidade_contas.xml',
        'views/contabilidade_livro_diario.xml',
        'views/contabilidade_livro_razao.xml',
        'views/contabilidade_balanco_patrimonial.xml',
        'views/contabilidade_dre.xml',
        'views/contabilidade_indicadores.xml',
        'data/contas_data.xml',
        # 'views/custom.xml',
        'views/menus.xml',
    ],
    'contributors': [
        'Brunno Bocardo <brunno.b@aluno.ifsp.edu.br>',
        'Mariana Lima <lima.mariana1@aluno.ifsp.edu.br>'
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}