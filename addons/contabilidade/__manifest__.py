{
    'name': 'Contabilidade',
    'description': 'Módulo para a aula de contabilidade',
    'version': '17.0',
    
    'depends': [
        'base',
        'web_responsive',
        'muk_web_appsbar',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/contabilidade_contas.xml',
        'views/menus.xml',
    ],
    'contributors': [
        'Brunno Bocardo <brunno.b@aluno.ifsp.edu.br>',
        'Mariana Lima <mariana.l@aluno.ifsp.edu.br>' # TODO: confirmar email
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}