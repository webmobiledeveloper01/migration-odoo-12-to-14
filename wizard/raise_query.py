# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models, fields


class ContractQuery(models.TransientModel):
    _name = 'contract.query'
    _description = 'Contract Query'

    def _get_query_check(self):
        if self._context.get('active_id', False):
            con_browse = self.env['res.contract'].\
                browse(self._context.get('active_id'))
            if con_browse.query_code_id:
                return True
        return False

    def _get_query_code(self):
        if self._context.get('active_id', False):
            con_browse = self.env['res.contract'].browse(
                self._context.get('active_id'))
            if con_browse.query_code_id:
                return con_browse.query_code_id.id
        return False

    note = fields.Text(
        'Query', required=True)
    query_code_id = fields.Many2one(
        'query.code', 'Query Code', required=True, default=_get_query_code)
    contract_id = fields.Many2one('res.contract', 'Contract',
                                  default=lambda self: self._context.get('active_id', False))
    query_check = fields.Boolean('Query Code Check', default=_get_query_check)

    # _defaults = {
    #     'contract_id': lambda self, cr, uid, c: c.get('active_id', False),
    # }

    
    def raise_query(self):
        contract_obj = self.env['res.contract'].browse(self._context['active_ids'])
        general_note = self.env['general.note']
        if 'active_ids' in self._context:
            for contract in contract_obj:

                create_note = {
                    'contract_id': contract.id,
                    'name': self.note,
                    'query_code_id': self.query_code_id.id,
                    'sale_name': contract.sale_name,
                    'log_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'create_date_note':
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'create_partner_id': contract.partner_id and
                    contract.partner_id.id or False,
                }

                general_note.sudo().create(create_note)
                if contract.state == 'query':
                    contract.write({'state': 'admin_query'})
                else:
                    contract.write({'state': 'query'})
                    if not contract.query_code_id:
                        contract.write(
                            {'query_code_id': self.query_code_id.id},
                            )
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
