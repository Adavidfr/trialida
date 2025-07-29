# -*- coding: utf-8 -*-

from odoo import _, models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class trialidaCuenta(models.Model):
    _name = 'trialida.cuenta'
    _description = 'Modelo de manejo de Cuentas de los socios'
    _rec_name = 'numero_cuenta'

    numero_cuenta = fields.Char('Numero de cuenta')
    socio_id = fields.Many2one('res.partner', string='Socio')
    fecha_apertura = fields.Datetime(        
        string='Fecha de apertura',
        default=fields.Datetime.now,
        readonly=True)
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
    
    prestamo_ids = fields.One2many(
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
        record['fecha_apertura'] = Datetime.now() 
    return super(trialidaCuenta, self).create(vals)

class trialidaMovimientos(models.Model):
    _name = 'trialida.movimientos'
    _description = 'Modelo de manejo de movimientos de Cuentas'

    cuenta_id = fields.Many2one('trialida.cuenta', string='Cuenta')
    codigo = fields.Char('Código')
    tipo_movimiento = fields.Selection([('deposito', 'Deposito'),
                                        ('retiro', 'Retiro'),
                                        ('tentrada', 'Transferencia Entrada'),
                                        ('tsalida', 'Transferencia Salida')])
    monto = fields.Float(string='Monto')
    fecha_movimiento = fields.Datetime(        
        string='Fecha de transferencia',
        default=fields.Datetime.now,
        readonly=True)
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
    codigo = fields.Char(string='Código', readonly=True)
    fecha_movimiento = fields.Datetime(        
        string='Fecha de transferencia',
        default=fields.Datetime.now,
        readonly=True)

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

class trialidaTransferencias(models.Model):
    _name = 'trialida.transferencias'
    _description = 'Modelo de manejo de Transferencias entre Cuentas'

    cuenta_origen_id = fields.Many2one('trialida.cuenta', string='Cuenta Origen', required=True)
    cuenta_destino_id = fields.Many2one('trialida.cuenta', string='Cuenta Destino', required=True)
    destinatario = fields.Many2one(related='cuenta_destino_id.socio_id', string='Destinatario', readonly=True)
    codigo = fields.Char(string='Código Transferencia')
    monto = fields.Float(string='Monto', required=True)
    fecha_transferencia = fields.Datetime(        
        string='Fecha de transferencia',
        default=fields.Datetime.now,
        readonly=True)
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
    agente_id = fields.Many2one('res.users', string='Agente de cuentas', readonly=True)
    monto = fields.Float(string='Monto')
    tasa_interes = fields.Float(string='Tasa de interés (%)')
    duracion = fields.Selection(
        selection=[
            ('3', '3 meses'),
            ('6', '6 meses'),
            ('9', '9 meses'),
            ('12', '12 meses')
        ],
        string='Duración (meses)',
        required=True
    )
    fecha_solicitud = fields.Datetime(        
        string='Fecha de transferencia',
        default=fields.Datetime.now,
        readonly=True)
    estado = fields.Selection([
        ('aprobado', 'Aprobado'),
        ('pendiente', 'Pendiente'),
        ('rechazado', 'Rechazado'),
    ], default='pendiente', string='Estado')

    fecha_desembolso = fields.Date(string='Fecha de desembolso', readonly=True)

    def action_aprobar(self):
        for record in self:
            record.estado = 'aprobado'
            record.fecha_desembolso = fields.Date.context_today(self)

    def action_rechazar(self):
        for record in self:
            record.estado = 'rechazado'


    amortizacion_line_ids = fields.One2many(
        'trialida.prestamo.linea',  # modelo hijo
        'prestamo_ids',              # campo Many2one en el modelo hijo que referencia a este modelo
        string='Líneas de amortización'
    )

    def calcular_amortizacion(self):
        for prestamo in self:
            prestamo.amortizacion_line_ids.unlink()
            if not prestamo.monto or not prestamo.tasa_interes or not prestamo.duracion:
                raise UserError("Debe ingresar monto, tasa de interés y duración.")
            monto = prestamo.monto
            tasa = prestamo.tasa_interes / 100.0 / 12.0
            n = int(prestamo.duracion)
            if tasa > 0:
                cuota = monto * (tasa * pow(1 + tasa, n)) / (pow(1 + tasa, n) - 1)
            else:
                cuota = monto / n
            saldo = monto

            fecha_base = prestamo.fecha_desembolso or fields.Date.context_today(prestamo)
            for i in range(1, n + 1):
                fecha_pago = fecha_base + relativedelta(months=i-1)
                interes = saldo * tasa
                capital = cuota - interes
                saldo -= capital
                prestamo.amortizacion_line_ids.create({
                    'prestamo_ids': prestamo.id,
                    'numero_cuota': i,
                    'fecha_pago': fecha_pago,
                    'cuota': round(cuota, 2),
                    'interes': round(interes, 2),
                    'capital': round(capital, 2),
                    'saldo': round(max(saldo, 0), 2),
                    'estado_pago': 'pendiente',
                })

    def enviar_solicitud(self):
        for prestamo in self:
            if prestamo.estado != 'pendiente':
                raise UserError(_("La solicitud ya fue enviada o procesada."))
            socio = prestamo.socio_id
            cuenta = self.env['trialida.cuenta'].search([('socio_id', '=', socio.id)], limit=1)
            if cuenta.user_id.id != self.env.uid:
                raise UserError(_(f"No puede solicitar un préstamo con una cuenta que no es suya. {cuenta.user_id.id}"))
            prestamo.estado = 'pendiente'
            prestamo.cuenta_id = cuenta.id
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': '¡Tu solicitud ha sido enviada!',
                    'type': 'rainbow_man',
                }
            }


class TrialidaPrestamoLinea(models.Model):
    _name = 'trialida.prestamo.linea'
    _description = 'Línea de amortización del préstamo'

    prestamo_ids = fields.Many2one('trialida.prestamo', string='Préstamo', ondelete='cascade')
    numero_cuota = fields.Integer(string='Número de cuota')
    fecha_pago = fields.Date(string='Fecha de desembolso')
    cuota = fields.Float(string='Cuota')
    interes = fields.Float(string='Interés')
    capital = fields.Float(string='Capital')
    saldo = fields.Float(string='Saldo')
    estado_pago = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado')
    ], string='Estado', default='pendiente')
    estado_desembolso = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('realizado', 'Realizado')
    ], string='Estado desembolso', compute='_compute_estado_desembolso', store=True)

    @api.depends('fecha_pago')
    def _compute_estado_desembolso(self):
        today = fields.Date.context_today(self)
        for linea in self:
            if linea.fecha_pago and linea.fecha_pago <= today:
                linea.estado_desembolso = 'realizado'
            else:
                linea.estado_desembolso = 'pendiente'