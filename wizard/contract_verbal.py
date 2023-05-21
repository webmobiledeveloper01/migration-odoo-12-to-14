# -*- coding: utf-8 -*-

import time

from openerp import netsvc
from odoo import api, models, fields, tools
from odoo.osv import osv


class ContractVerbalOpen(models.Model):
    _name = 'contract.verbal.open'
    _description = 'Contract Verbal Open'

    def _get_mpan_code(self):
        mpan_code = ''
        if self._context.get('active_id'):
            # con_obj = self.env['res.contract'].browse(
            #     self._context.get('active_id', False))
            con_obj = self.env['res.contract'].browse(self._context['active_id'])
            if con_obj.meter_data_line:
                for con_meter_data in con_obj.meter_data_line:
                    mpan_code = con_meter_data.mpan_code
        return mpan_code

    
    def _get_verbal_text(self):
        obj_contract = self.env['res.contract']
        values = {'body_html': False}
        if self._context.get('active_id'):
            contract = obj_contract.browse(self._context['active_id'])
            ctx = self._context
            new_context = {'current_datetime':
                            time.strftime('%Y-%m-%d %H:%M:%S')}
            template_search_id = \
                self.env['electronic.verification'].with_context(new_context).search(
                    [('category_id', '=', contract.categ_id.id),
                     ('contract_type_id', '=',
                      contract.contract_type_id.id),
                     ('partner_id', '=', contract.supplier_id.id),
                     ('company_id', '=', contract.company_id.id),
                     ('type', '=', 'verbal')])
            if not template_search_id:
                raise osv.except_osv(('Invalid Data!'),
                                     ("There is a no template defined \
                                         for %s") % (
                                         contract.supplier_id.name))
            template_id = \
                self.env['electronic.verification'].with_context(new_context).browse(
                    template_search_id[0],
                ).template_id.id
            template = self.env['email.template'].browse(template_id)
            values['body_html'] = \
                self.env['mail.template'].render_template(
                    getattr(template, 'body_html'),
                    template.model, ctx['active_ids'][0], context=ctx) or False
            values['body_html'] = tools.html_sanitize(values['body_html'])
        return values['body_html'] or ''

    verbal_text = fields.Html('Text to Read', default=_get_verbal_text)
    is_agreed = fields.Boolean('Agreed ?', required=True, default=True)
    partner_id = fields.Many2one('res.partner', 'Customer')
    user_id = fields.Many2one('res.users', 'Agent Name')
    mpan_code = fields.Char('MPAN Code', size=64)
    con_end_date = fields.Date('Contract End Date')
    check_branch_contract = fields.Boolean('Branch Contract')
    contract_line =\
        fields.One2many('res.contract', 'verbal_contract_id', 'Contract')

    # _defaults = {
    #     'verbal_text': _get_verbal_text,
    #     'is_agreed': True,
    #     'partner_id': lambda obj, cr, uid, context: context and
    #     context.get('active_id', False) and
    #     obj.pool.get('res.contract').browse(
    #         cr, uid, context.get('active_id', False),
    #         context=context).partner_id.id or False,
    #     'user_id': lambda obj, cr, uid, context: context and
    #     context.get('active_id', False) and
    #     obj.pool.get('res.contract').browse(
    #         cr, uid, context.get('active_id', False),
    #         context=context).user_id.id or False,
    #     'con_end_date': lambda obj, cr, uid, context: context and
    #     context.get('active_id', False) and
    #     obj.pool.get('res.contract').browse(
    #         cr, uid, context.get('active_id', False),
    #         context=context).end_date or False,
    #     'mpan_code': _get_mpan_code,
    #     'check_branch_contract': False,
    # }

    # 
    # def change_inv_state(self):
    #     wf_service = netsvc.LocalService("workflow")
    #     obj_contract = self.pool.get('res.contract')
    #     if context is None:
    #         context = {}
    #     for self_obj in self.browse(cr, uid, ids, context=context):
    #         if 'active_ids' in context:
    #             wf_service.trg_validate(uid, 'res.contract',
    #                                     context['active_ids'][0],
    #                                     'act_sale_agreed', cr)
    #             obj_contract.write(
    #                 cr, uid, [context['active_ids'][0]],
    #                 {'confirmation_via': 'verbal',
    #                  'confirmation_date':
    #                  fields.date.context_today(self, cr, uid, context=context),
    #                  'confirmation_medium': 'ver'}, context=context)
    #             search_renew_id = obj_contract.search(
    #                 cr, uid, [('renew_id', '=', context['active_ids'][0])])
    #             if search_renew_id:
    #                 obj_contract.write(
    #                     cr,
    #                     uid,
    #                     search_renew_id, {'superseded': True},
    #                     context=context)
    #         if self_obj.contract_line:
    #             for branch_con in self_obj.contract_line:
    #                 if branch_con.branch_con_check:
    #                     wf_service.trg_validate(uid, 'res.contract',
    #                                             branch_con.id,
    #                                             'act_sale_agreed', cr)
    #                     obj_contract.write(
    #                         cr,
    #                         uid, [branch_con.id], {
    #                             'confirmation_via': 'verbal',
    #                             'confirmation_date': fields.date.context_today(
    #                                 self, cr, uid, context=context),
    #                             'confirmation_medium': 'ver'
    #                         },
    #                         context=context)
    #                     search_renew_id = obj_contract.search(
    #                         cr, uid, [('renew_id', '=', branch_con.id)])
    #                     if search_renew_id:
    #                         obj_contract.write(
    #                             cr,
    #                             uid,
    #                             search_renew_id, {'superseded': True},
    #                             context=context)
    #     return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
