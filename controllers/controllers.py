# -*- coding: utf-8 -*-
# from odoo import http


# class Coacsemdos(http.Controller):
#     @http.route('/coacsemdos/coacsemdos', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/coacsemdos/coacsemdos/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('coacsemdos.listing', {
#             'root': '/coacsemdos/coacsemdos',
#             'objects': http.request.env['coacsemdos.coacsemdos'].search([]),
#         })

#     @http.route('/coacsemdos/coacsemdos/objects/<model("coacsemdos.coacsemdos"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('coacsemdos.object', {
#             'object': obj
#         })

