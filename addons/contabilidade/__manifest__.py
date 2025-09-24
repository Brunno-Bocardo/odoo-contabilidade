{
    'name': 'Contabilidade',
    'description': 'Módulo para a aula de contabilidade',
    'version': '17.0',
    
    'depends': [
        'base',
        'web_responsive',
        'muk_web_appsbar',
    ],
    "assets": {
        "web.assets_backend": [
            # "contabilidade/static/src/scss/dark_theme.scss",
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/contabilidade_contas.xml',
        'views/contabilidade_livro_diario.xml',
        'views/contabilidade_livro_razao.xml',
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