# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging


_logger = logging.getLogger(__name__)


class DocusignMailWizard(models.TransientModel):
    _name = 'docusign.mail.wiz'
    _description = "Docusign Mail Wiz"

    template_id = fields.Many2one('ir.actions.report', string='Docusign Template')
    loa_attached = fields.Boolean('LOA Attached')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('customer', '=', True)])
    payment_type_bool = fields.Boolean('Payment Type(DD)')
    partner_ids = fields.Many2many('res.partner', string='Recipients', domain=[('customer', '=', True)])
    # attachment_ids = fields.Many2many
    subject = fields.Char('Subject')
    body = fields.Html('Contents', help='Automatically sanitized HTML contents')
    res_id = fields.Integer('Related Document ID')
    models = fields.Char('Related Document Model', size=128)
    author_id = fields.Many2one('res.partner', string='Author')
    message_id = fields.Char('Message-Id', help='Message unique identifier')
    attachment_ids = fields.Many2many('ir.attachment', 'docusign_message_attachment_rel',
                                      'docusign_message_id', 'attachment_id', string='Attachments')
    # docusign_template_id = fields.Many2one('docusign.template', string='Doc Template')

    # 
    # def create_attachment(self):
    #     for rec in self:
    #
    #         return True

    @api.model
    def default_get(self, fields):
        res = super(DocusignMailWizard, self).default_get(fields)
        sale_order_id = self.env['res.contract'].browse(self._context.get('active_id'))
        if sale_order_id.env.context.get('sale_menu', False):
            print ('--print partner id from sale order::>>>', sale_order_id.partner_id)
            res['partner_id'] = sale_order_id.designated_part_id.id or False
            res['supplier_id'] = sale_order_id.sale_supplier_id.id or False

        if sale_order_id.env.context.get('contract_menu', False):
            print ('--des partner id in contract menu :::>>>', sale_order_id.des_partner_id)
            res['partner_id'] = sale_order_id.des_partner_id.id or False
            res['supplier_id'] = sale_order_id.supplier_id.id or False

        return res

    @api.onchange('partner_id')
    def onchange_subject_partner_ids(self):
        # import base64
        sale_order_id = self.env['res.contract'].browse(self._context.get('active_id'))
        # loa_contract = self.env.ref('dernetz.report_loa_crm_contract').id
        sale_order_subject = 'Dernetz ' + '(Ref ' + sale_order_id.sale_name + ')'
        contract_subject = 'Dernetz ' + '(Ref ' + sale_order_id.contract_name + ')'
        if self.partner_id:
            if sale_order_id.env.context.get('sale_menu', False):
                self.subject = sale_order_subject
                self.partner_ids = [(4, sale_order_id.designated_part_id[0].id, 0)]
                # self.template_id = loa_contract

            if sale_order_id.env.context.get('contract_menu', False):
                self.subject = contract_subject
                self.partner_ids = [(4, sale_order_id.des_partner_id[0].id, 0)]
                # self.template_id = loa_contract

    # 
    # def create_attachment(self):
    #     ir_model_data = self.env['ir.model.data']
    #     try:
    #         template_id = ir_model_data.get_object_reference('dernetz', 'report_loa_crm_contract')[1]
    #         print ('--printed template id ::>>', template_id)
    #     except ValueError:
    #         template_id = False
    #     try:
    #         compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
    #         print ('--printed compose form id ::>>>', compose_form_id)
    #     except ValueError:
    #         compose_form_id = False
    #     ctx = {
    #         # 'default_model': 'res.contract',
    #         # 'default_res_id': self.ids[0],
    #         # 'default_use_template': bool(template_id),
    #         'default_template_id': template_id,
    #         # 'default_composition_mode': 'comment',
    #         # 'mark_so_as_sent': True,
    #         # 'custom_layout': "mail.mail_notification_paynow",
    #         # 'proforma': self.env.context.get('proforma', False),
    #         # 'force_email': True
    #     }
    #     return {
    #         'type': 'ir.actions.act_window',
    #         # 'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form_id, 'form')],
    #         'view_id': compose_form_id,
    #         'target': 'new',
    #         'context': ctx,
    #     }

    
    def send_loa_mail(self):
        login_user = self.env.uid
        for rec in self:
            email_to = rec.partner_id.email
            docusign_template = self.env['docusign.document'].create({
                'author_id': login_user or False,
                # 'email_from':login_user and login_user.email and
                #              login_user.name + ' <' + login_user.email + '>' or False,
                'email_to': email_to,
                'body_html': rec.body,
                'model': self._context['active_model'],
                'res_id': self._context['active_id'],
                'attachment_ids':
                    [(6, 0, [attach.id
                             for attach in rec.attachment_ids])],
                'partner_ids':
                    [(6, 0, rec.partner_ids.ids)],
                'date': datetime.now(),
                'subject': rec.subject,
                'state': 'draft',

            })
        return True
