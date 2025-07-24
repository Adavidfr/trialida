from odoo import models, fields, api

class ResPartner(models.Model):
     _inherit = 'res.partner'
     _description = 'Modelo para aumentar funcionalidad de partners'

     identification_type = fields.Selection([('cedula', 'Cédula'),
                                             ('ruc', 'RUC'),
                                             ('passport', 'Passport')],
                                            string='Identificador')
     state = fields.Selection([('active', 'Active'),
                               ('inactive', 'Inactive'),
                               ('suspended', 'Suspendido')], default='active')
     company_name = fields.Char(string='Lugar de trabajo')
     company_phone = fields.Char(string='teléfono de trabajo')
     company_email = fields.Char(string='correo de trabajo')
     company_address = fields.Char(string='Dirección de trabajo')