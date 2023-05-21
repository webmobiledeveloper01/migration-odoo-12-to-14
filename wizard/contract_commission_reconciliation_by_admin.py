# -*- coding: utf-8 -*-
from datetime import datetime
import time

from odoo import api, models, fields


class WizardContractCommRecSysadmin(models.TransientModel):
    _name = 'wizard.contract.comm.rec.sysadmin'
    _description = "Wizard Contract Comm Rec Sysadmin"

    # def onchange_report_type(self, cr, uid, ids, type, context=None):
    #     res = {'value': {}}
    #     if type != 'all':
    #         res['value'] = {'final_bool': False}
    #     return res

    date_from = fields.Date(
        "Start Date", required=True, default=time.strftime("%Y-01-01"))
    # users_line = fields.One2many('res.users.contract.commission',
    #                               'wizard_id', 'Users Line')
    type = fields.Selection(
        [('all', 'All'), ('selected', 'Selected')], 'Type', required=True, default='all')
    final_bool = fields.Boolean('Final', default=False)
    mpan_bool = fields.Boolean('MPAN/MPR', default=False)

    # def print_report(self, cr, uid, ids, context=None):
    #     data = self.read(cr, uid, ids)[0]
    #     today = datetime.strptime(data['date_from'], "%Y-%m-%d")
    #     date_ref = today.strftime('%Y') + '_' + today.strftime('%m')
    #
    #     report_name = 'Commission_Report(All)_%s' % (str(date_ref))
    #     return {
    #         'type': 'ir.actions.report.xml',
    #         'report_name': 'contract_commission_rec_by_system_admin',
    #         'datas': data,
    #         'name': report_name
    #     }
    #
    # def print_report_xls(self, cr, uid, ids, context=None):
    #     data = self.read(cr, uid, ids)[0]
    #     today = datetime.strptime(data['date_from'], "%Y-%m-%d")
    #     date_ref = today.strftime('%Y') + '_' + today.strftime('%m')
    #
    #     report_name = 'Commission_Report(All)_%s' % (str(date_ref))
    #     return {
    #         'type': 'ir.actions.report.xml',
    #         'report_name': 'contract_commission_rec_by_system_admin_xls',
    #         'datas': data,
    #         'name': report_name
    #     }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
