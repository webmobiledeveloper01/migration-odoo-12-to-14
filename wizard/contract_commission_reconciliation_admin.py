from odoo import api, fields, models


class WizardContractCommRecSysadmin(models.TransientModel):
    _name = 'wizard.contract.comm.rec.sysadmin'
    _description = "Wizard Contract Comm Rec Sysadmin"

    date_from = fields.Date(string="Start Date", required=True)
    # users_line = fields.One2many('res.users.contract.commission','wizard_id', string='Users Line')
    type = fields.Selection([('all', 'All'), ('selected', 'Selected')], 'Type', required=True)
    final_bool = fields.Boolean(string='Final')
    mpan_bool = fields.Boolean(string='MPAN/MPR')
