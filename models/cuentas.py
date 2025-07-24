# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class trialidaCuenta(models.Model):
    _name = 'trialida.cuenta'
    _description = 'Modelo de manejo de Cuentas de los socios'
    _rec_name = 'numero_cuenta'

    numero_cuenta = fields.Char('Numero de cuenta')
    socio_id = fields.Many2one('res.partner', string='Socio')
    fecha_apertura = fields.Date('Fecha de apertura')
    saldo_actual = fields.Float(string='Saldo actual')
    estado = fields.Selection([
        ('active', 'Activa'),
        ('close', 'Cerrada'),
        ('suspend', 'Suspendida')
    ])
    tipo_cuenta = fields.Selection([
        ('ahorros', 'ahorro'),
        ('corriente', 'corriente')
    ])
    user_id = fields.Many2one('res.users', string='Usuario')

    movimiento_id = fields.One2many(
        'trialida.movimientos', 'cuenta_id', string='Movimiento')

    transferencia_id = fields.One2many(
        'trialida.transferencias', 'cuenta_origen_id', string='Transferencia')
    
    prestamo_id = fields.One2many(
        'trialida.prestamo', 'cuenta_id', string='Préstamos')


    @api.model_create_multi
    def create(self, vals):
        for record in vals:
            if record.get('socio_id'):
                partner = self.env['res.partner'].browse(record.get('socio_id'))
                user = self.env['res.users'].search([('partner_id', '=', partner.id)])
                record['user_id'] = user.id
                seq = self.env.ref('trialida.seq_trialida_cuentas').next_by_code('trialida.cuentas')
                record['numero_cuenta'] = seq 
        return super(trialidaCuenta, self).create(vals)



class trialidaMovimientos(models.Model):
    _name = 'trialida.movimientos'
    _description = 'Modelo de manejo de movimientos de Cuentas'

    cuenta_id = fields.Many2one('trialida.cuenta', string='Cuenta')
    codigo = fields.Char('Çódigo')
    tipo_movimiento = fields.Selection([('deposito', 'Deposito'),
                                        ('retiro', 'Retiro'),
                                        ('tentrada', 'Transferencia Entrada'),
                                        ('tsalida', 'Transferencia Salida')])
    monto = fields.Float(string='Monto')
    fecha_movimiento = fields.Datetime('Fecha de movimiento')
    descripcion = fields.Char(string='Descripcion')
    saldo_post_movimiento = fields.Float(string='Saldo post movimiento')


class trialidaOperaciones(models.TransientModel):
    _name = 'trialida.operaciones'
    _description = 'Modelo de manejo de operaciones de Cuentas'

    cuenta_id = fields.Many2one('trialida.cuenta', string='Cuenta')
    socio = fields.Many2one(related='cuenta_id.socio_id', string='socio')
    saldo = fields.Float(related='cuenta_id.saldo_actual', string='Saldo actual')
    tipo_movimiento = fields.Selection([('deposito', 'Deposito'),
                                        ('retiro', 'Retiro')])
    monto = fields.Float(string='Monto')
    descripcion = fields.Char(string='Descripcion')

    def aceptar_operacion(self):
        if self.tipo_movimiento == 'deposito':
            op = self.monto + self.cuenta_id.saldo_actual
        elif self.tipo_movimiento == 'retiro':
            if self.monto > self.cuenta_id.saldo_actual:
                raise UserError(f'Saldo insuficiente de la cuenta {self.cuenta_id.numero_cuenta}')
            op = self.cuenta_id.saldo_actual - self.monto

        seq= self.env.ref('trialida.seq_trialida_movimientos').next_by_code('trialida.movimientos')
        val = {'cuenta_id': self.cuenta_id.id,
               'codigo': seq,
               'tipo_movimiento': self.tipo_movimiento,
               'descripcion': self.descripcion,
               'saldo_post_movimiento': op,
               'monto': self.monto,}

        self.env['trialida.movimientos'].create(val)
        self.cuenta_id.saldo_actual = op
        # cuenta_obj = self.env['trialida.cuenta'].browse(self.cuenta_id.id)
        # cuenta_obj.write({'saldo_actual': op})
        # self.env['trialida.cuenta'].write({'saldo_actual': op})

class trialidaTransferencias(models.Model):
    _name = 'trialida.transferencias'
    _description = 'Modelo de manejo de Transferencias entre Cuentas'

    cuenta_origen_id = fields.Many2one('trialida.cuenta', string='Cuenta Origen', required=True)
    cuenta_destino_id = fields.Many2one('trialida.cuenta', string='Cuenta Destino', required=True)
    destinatario = fields.Many2one(related='cuenta_destino_id.socio_id', string='Destinatario', readonly=True)
    codigo = fields.Char(string='Código Transferencia')
    monto = fields.Float(string='Monto', required=True)
    fecha_transferencia = fields.Datetime('Fecha de Transferencia')
    estado = fields.Selection([('pendiente', 'Pendiente'),
                               ('completado', 'Completado'),
                               ('cancelada', 'Cancelada')],
                              default='pendiente')
    referencia = fields.Char(string='Referencia')

    @api.model_create_multi
    def create(self, vals):
        for record in vals:
            if not record.get('codigo'):
                seq = self.env.ref('trialida.seq_trialida_transferencias').next_by_code('trialida.transferencias')
                record['codigo'] = seq

        return super().create(vals)

    def realizar_transferencia(self):
        for transferencia in self:
            if transferencia.monto <= 0:
                raise UserError('El monto debe ser mayor a cero.')

            if transferencia.cuenta_origen_id.id == transferencia.cuenta_destino_id.id:
                raise UserError('No se puede transferir a la misma cuenta.')

            if transferencia.monto > transferencia.cuenta_origen_id.saldo_actual:
                raise UserError(f'Saldo insuficiente en la cuenta {transferencia.cuenta_origen_id.numero_cuenta}.')

            # Generar código
            seq = self.env.ref('trialida.seq_trialida_movimientos').next_by_code('trialida.movimientos')
            fecha = datetime.now()

            # Actualizar saldos
            cuenta_origen = transferencia.cuenta_origen_id
            cuenta_destino = transferencia.cuenta_destino_id

            cuenta_origen.saldo_actual -= transferencia.monto
            cuenta_destino.saldo_actual += transferencia.monto

            # Crear movimiento de salida
            self.env['trialida.movimientos'].create({
                'cuenta_id': cuenta_origen.id,
                'codigo': seq,
                'tipo_movimiento': 'tsalida',
                'monto': transferencia.monto,
                'fecha_movimiento': fecha,
                'descripcion': f'Transferencia a {cuenta_destino.numero_cuenta}',
                'saldo_post_movimiento': cuenta_origen.saldo_actual
            })

            # Crear movimiento de entrada
            self.env['trialida.movimientos'].create({
                'cuenta_id': cuenta_destino.id,
                'codigo': seq,
                'tipo_movimiento': 'tentrada',
                'monto': transferencia.monto,
                'fecha_movimiento': fecha,
                'descripcion': f'Transferencia desde {cuenta_origen.numero_cuenta}',
                'saldo_post_movimiento': cuenta_destino.saldo_actual
            })

            # Registrar datos de la transferencia
            transferencia.codigo = seq
            transferencia.fecha_transferencia = fecha
            transferencia.estado = 'completado'

    def imprimir_comprobante(self):
        # Esto llama al reporte registrado con xmlid 'trialida.action_report_transferencia'
        return self.env.ref('trialida.action_report_transferencia').report_action(self)


class TrialidaPrestamo(models.Model):
    _name = 'trialida.prestamo'
    _description = 'Préstamos'

    socio_id = fields.Many2one('res.partner', string='Socio')
    cuenta_id = fields.Many2one('trialida.cuenta', string='Cuenta')
    monto = fields.Float(string='Monto')
    tasa_interes = fields.Float(string='Tasa de interés (%)')
    duracion = fields.Integer(string='Duración (meses)')
    fecha_otorgamiento = fields.Date(string='Fecha de otorgamiento')
    estado = fields.Selection([
        ('aprobado', 'Aprobado'),
        ('pendiente', 'Pendiente'),
        ('rechazado', 'Rechazado'),
    ], default='pendiente', string='Estado')

    def action_aprobar(self):
        for record in self:
            record.estado = 'aprobado'

    def action_rechazar(self):
        for record in self:
            record.estado = 'rechazado'


    amortizacion_line_ids = fields.One2many(
        'trialida.prestamo.linea',  # modelo hijo
        'prestamo_id',              # campo Many2one en el modelo hijo que referencia a este modelo
        string='Líneas de amortización'
    )

    def calcular_amortizacion(self):
        # Aquí iría tu lógica para calcular la tabla de amortización
        # Ejemplo simple: crear líneas vacías o con datos dummy para probar la vista
        self.amortizacion_line_ids.unlink()  # borrar líneas previas
        for i in range(1, self.duracion + 1):
            self.env['trialida.prestamo.linea'].create({
                'prestamo_id': self.id,
                'numero_cuota': i,
                'fecha_pago': False,
                'cuota': 0.0,
                'interes': 0.0,
                'capital': 0.0,
                'saldo': 0.0,
                'pagado': False,
            })

class TrialidaPrestamoLinea(models.Model):
    _name = 'trialida.prestamo.linea'
    _description = 'Línea de amortización del préstamo'

    prestamo_id = fields.Many2one('trialida.prestamo', string='Préstamo', ondelete='cascade')
    numero_cuota = fields.Integer(string='Número de cuota')
    fecha_pago = fields.Date(string='Fecha de pago')
    cuota = fields.Float(string='Cuota')
    interes = fields.Float(string='Interés')
    capital = fields.Float(string='Capital')
    saldo = fields.Float(string='Saldo')
    pagado = fields.Boolean(string='Pagado', default=False)