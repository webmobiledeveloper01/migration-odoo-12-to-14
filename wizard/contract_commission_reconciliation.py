from datetime import datetime
import time

from odoo import api, models, fields


class WizardContractCommissionReconciliation(models.TransientModel):
    _name = 'wizard.contract.commission.reconciliation'
    _description = "Wizard Contract Comm Reconciliation"

    date_from = fields.Date("Start Date", required=True, default=time.strftime("%Y-01-01"),)

    
    def print_report(self):
        today = datetime.strptime(self.date_from, "%Y-%m-%d")
        date_ref = today.strftime('%Y') + '_' + today.strftime('%m')

        # user = self.env['res.users'].browse(self.env.uid).name or ''
        print ('---print---user id :::>>>>>', self.env.uid)
        user = self.env.user.name or ''
        report_name = 'Commission_Report_' + user + '_%s' % (str(date_ref))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'contract_commission_reconciliation',
            'datas': self.read(),
            'name': report_name,
        }

    
    def print_report_xls(self):
        today = datetime.strptime(self.date_from, "%Y-%m-%d")
        date_ref = today.strftime('%Y') + '_' + today.strftime('%m')

        # user = self.pool.get('res.users').browse(self.env.uid).name or ''
        user = self.env.user.name or ''
        report_name = 'Commission_Report_' + user + '_%s' % (str(date_ref))
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'contract_commission_reconciliation_xls',
            'datas': self.read(),
            'name': report_name,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
