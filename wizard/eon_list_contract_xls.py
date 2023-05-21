# -*- coding: utf-8 -*-

import xlwt

from odoo import api, models, fields

ezxf = xlwt.easyxf


class EonListContractXls(models.TransientModel):
    _name = 'eon.list.contract.xls'
    _description = 'Export List of contracts'

    
    def _get_partner_id(self):
        supp_id = self.env['res.partner'].search(
            [('name', '=', 'EON'), ('supplier', '=', True)])
        return supp_id.ids[0] or False

    partner_id = fields.Many2one('res.partner', 'Supplier', default=_get_partner_id)
    contract_line_ids = fields.Many2many(
        'res.contract',
        'res_contract_copy_wizard_rel',
        'eon_contract_xls_id',
        'contract_id',
        'Contract Line',
        required=True)

    
    def generate_eon_xls(self):
        data = {}
        data['form'] = self.read(self.ids, ['contract_line_ids'])[0]
        contract_ids = data['form']['contract_line_ids']
        datas = {'ids': contract_ids, 'model': 'res.contract', 'form': data}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'eon_list_contract',
            'datas': datas,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
