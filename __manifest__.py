# -*- coding: utf-8 -*-
{
    'name': "trialida",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base'],

    'data': [
        'data/users_data.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/views_trialida_cuenta.xml',
        'data/sequence_data.xml',
        'views/view_trialida_operaciones.xml',
        'views/report_transferencia.xml',
        'views/view_trialida_transferencias.xml',
        'views/view_trialida_prestamo.xml',
    ],

    'installable': True,
    'application': True,
}

