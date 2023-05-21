from odoo import api, models, fields, _


class CrmCaseSection(models.Model):
    """ inherited Model for sales teams. """

    _inherit = "crm.team"

    broker_split = fields.Integer('Broker Split', default=100)
    upfront_payment = fields.Integer('Upfront Payment', default=100)
    # 'broker_percentage_split': fields.integer('Broker Percentage Split'),
    vatable = fields.Boolean('VATable')
    vat_rate = fields.Float('VAT Rate', default=20)
    partner_ids = fields.Many2many('res.partner', 'crm_partner_rel',
                                    'partner_id', 'crm_id', 'Partners',
                                    domain="[('supplier','=',False),('customer','=',False)]")
    external_broker = fields.Boolean('External Broker', default=False)
    note = fields.Text('Note')

    def _check_payments_confi_value(self):
        for sale_team in self:
            if sale_team.broker_split > 100:
                return False
            if sale_team.upfront_payment > 100:
                return False
            if sale_team.broker_split > 100 or sale_team.broker_split < 0:
                return False
        return True

    def _check_broker_split(self):
        for sale_team in self:
            if sale_team.broker_split > 100 or sale_team.broker_split < 0:
                return False
        return True

    _constraints = [
        (_check_payments_confi_value,
         '\nError !\n\n You can not set value greater then 100 !',
         ['broker_split', 'upfront_payment']),
        (_check_broker_split,
         '\nError !\n\n You must be set value between 0 to 100',
         ['broker_split']),
    ]
