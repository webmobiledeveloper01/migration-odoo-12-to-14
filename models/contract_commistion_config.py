from odoo import api, fields, models
from datetime import datetime


class ContractCommissionConfi(models.Model):
    _name = "contract.commission.confi"
    _description = "Contract Commission Config"
    _rec_name = "year_duration"
    rec_name = "year_duration"

    year_duration = fields.Selection([('1', '1 Year'), ('2', '2 Years'), ('3', '3 Years'), ('4', '4 Years'),
                                      ('5', '5 Years')], string='Duration')
    percentage = fields.Float(string='Percentage')
    external_broker = fields.Boolean(string='External Broker')
    # supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)])
    supplier_id = fields.Many2one('res.partner', string='Supplier')


class ContractCommissionReconcile(models.Model):
    _name = "contract.commission.reconcile"
    _description = "Contract Commission Reconcile"

    dummy_create_datetime_commission = fields.Datetime(string='Creation DateTime')
    create_datetime_commission = fields.Datetime(string='Creation DateTime')
    create_datetime = fields.Datetime(string='Creation DateTime')
    dummy_user_id = fields.Many2one('res.users', string="User")
    user_id = fields.Many2one('res.users', string="User")
    receipt_date = fields.Date(string='Receipt Date')
    receipt_reference = fields.Char(string='Receipt Reference')
    com_amount = fields.Float(string='Amount')
    com_deducted_amount = fields.Float(string='Remaining')
    contract_id = fields.Many2one('res.contract', string='Contract')
    comm_deducted_amount = fields.Float(string='Remaining')
    # 'comm_deducted_amount':
    # fields.function(_calculate_com_deducted_total,
    #                 string='Remaining', type="float", method=True,
    #                 store={'contract.commission.reconcile':
    #                        (lambda self, cr, uid, ids, context=None: ids,
    #                         ['com_amount', 'contract_id'], 10),
    #                        'res.contract': (_get_contract,
    #                                         ['commission_reconcile_ids',
    #                                          'commission_amount_total',
    #                                          'broker_commission'], 10), }),
    consumption = fields.Float(string='Consumption')

    @api.model
    def default_get(self, fields):
        res = super(ContractCommissionReconcile, self).default_get(fields)
        res['create_datetime_commission'] = datetime.now()
        res['user_id'] = self.env.uid
        return res


class SupplierCommissionConfi(models.Model):

    _name = "supplier.commission.confi"
    _description = "Supplier Commission Config"
    _rec_name = "supplier_id"

    # supplier_id = fields.Many2one('res.partner', 'Supplier', domain=[('supplier', '=', True)])
    supplier_id = fields.Many2one('res.partner', 'Supplier')
    year_duration = fields.Selection([('1', '1 Year'), ('2', '2 Years'), ('3', '3 Years'),
                                      ('4', '4 Years'), ('5', '5 Years')], string='Duration')
    percentage = fields.Float(string='Percentage')

# class broker_commition_reconcile(models.Model):
#     _name = "broker.commission.reconcile"
#
#     dummy_create_datetime_commission = fields.Datetime(string='Creation DateTime')
#     create_datetime_commission = fields.Datetime(string='Creation DateTime')
#     create_datetime = fields.Datetime(string='Creation DateTime')
#     dummy_user_id = fields.Many2one('res.users', string="User")
#     user_id = fields.Many2one('res.users', string="User")
#     receipt_date = fields.Date(string='Adjustment Month')
#     receipt_reference = fields.Char(stirng='Receipt Reference')
#     com_amount = fields.Float(string='Amount')
#     contract_id = fields.Many2one('res.contract', string='Contract')
#     ext_contract_id = fields.Many2one('res.contract', string='Contract')
#     # check_accuracy = fields.Related('contract_id', 'check_accuracy',type='boolean',relation='res.contract',
#       string="Contract")
#     # partner_id = fields.Related('contract_id', 'partner_id',type='many2one',relation='res.partner',string="Partner")
#     # usage = fields.Related('contract_id', 'usage',type='float',relation='res.contract',string="Usage")
#     is_external_broker = fields.Boolean(string='IS External ?')
