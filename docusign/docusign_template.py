from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import osv


class DocusignTemplate(models.Model):
    _name = 'docusign.template'
    _description = "Docusign Template"

    name = fields.Char('Name')
    model_id = fields.Many2one('ir.model', string='Applies to', help="The kind of document with \
                                            with this template can be used")
    model = fields.Char(related='model_id.model', string='Related Document Model', size=128, store=True)
    signhere_tab = fields.Char('Signhere Tab', size=128)
    signhere_tab_date = fields.Char('Signhere Date Tab', size=128)
    xoff = fields.Float('XOFF')
    yoff = fields.Float('YOFF')
    xoff_date = fields.Float('XOFF Date')
    yoff_date = fields.Float('YOFF Date')
    lang = fields.Char('Language')
    user_signature = fields.Boolean('Add Signature', help="If checked, the user's signature will be \
                               appended to the text version of the message")
    subject = fields.Char('Subject', translate=True, help="Subject (placeholders may be used here)")
    email_from = fields.Char('From', help="Sender address (placeholders may be used \
                            here). If not set, the default value will be the \
                            author's email alias if configured, or email \
                            address.")
    email_to = fields.Char('To (Emails)', help="Comma-separated recipient addresses \
                            (placeholders may be used here)")
    email_recipients = fields.Char('To (Partners)', help="Comma-separated ids of recipient partners \
                            (placeholders may be used here)")
    email_cc = fields.Char('Cc', help="Carbon copy recipients (placeholders may \
                            be used here)")
    reply_to = fields.Char('Reply-To', help="Preferred response address (placeholders \
                            may be used here)")
    mail_server_id = fields.Many2one('docusign.config', string='Outgoing Mail Server',
                                     help="Optional preferred server for \
                                outgoing mails. If not set, the highest \
                                priority one will be used.")
    body_html = fields.Text('Body', translate=True, help="Rich-text/HTML version of the message \
                            (placeholders may be used here)")
    report_name = fields.Char('Report Filename', translate=True, help="Name to use for the generated report file \
                            (may contain placeholders)\n The extension can \
                            be omitted and will then come from the \
                            report type.")
    report_template = fields.Many2one('ir.actions.report', string='Optional report to print and attach')
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', string='Sidebar action',
                                        help="Sidebar action to make this template \
                                available on records of the related \
                                document model")
    ref_ir_value = fields.Many2one('ir.values', string='Sidebar Button', help="Sidebar button to open the sidebar \
                                action")
    attachment_ids = fields.Many2many('ir.attachment', 'docusign_template_attachment_rel', 'docusign_template_id',
                                      'attachment_id', string='Attachments',
                                      help="You may attach files to this template, \
                                 to be added to all emails created from \
                                 this template")
    auto_delete = fields.Boolean('Auto Delete', default=True, help="Permanently delete this email after \
                               sending it, to save space")
    model_object_field = fields.Many2one('ir.model.fields', string="Field", help="Select target field from the related \
                                document model.\n If it is a relationship \
                                field you will be able to select a target \
                                field at the destination of the \
                                relationship.")

    sub_object = fields.Many2one('ir.model', string='Sub-model', help="When a relationship field is selected \
                                as first field, this field shows the document \
                                model the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', string='Sub-field',
                                             help="When a relationship field is selected \
                                as first field, this field lets you select \
                                the target field within the destination \
                                document model (sub-model).")
    null_value = fields.Char('Default Value', help="Optional value to use if the \
                                          target field is empty")
    copyvalue = fields.Char('Placeholder Expression', help="Final placeholder expression, \
                                         to be copy-pasted in the desired \
                                         template field.")

    
    def create_action(self):
        vals = {}
        action_obj = self.env['ir.actions.act_window']
        data_obj = self.env['ir.model']
        print ('---printed valasss::>>>>>>>>', vals)
        for template in self:
            src_obj = template.model_id.model
            print ('-----printed src objetc::>>>>>', src_obj)
            # model_data_id = data_obj._get_id(
            #     cr, uid, 'dernetz',
            #     'docusign_email_compose_message_wizard_form')
            model_data_id = self.env.ref('dernetz.docusign_mail_wizard_form').id
            print ('---printed modeldata id :>>>>>>', model_data_id)
            # res_id = data_obj.browse(
            #     cr, uid, model_data_id, context=context).res_id
            res_id = data_obj.sudo().search([('id', '=', model_data_id)])
            print ('------printed res id :>>>>>', res_id)
            button_name = ('Docusign Mail (%s)') % template.name
            vals['ref_ir_act_window'] = action_obj.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'docusign.mail.wiz',
                'src_model': src_obj,
                # 'view_type': 'form',
                'context': {'default_composition_mode': 'mass_mail',
                            'default_template_id': template.id,
                            'default_use_template': True},
                'view_mode': 'form,tree',
                'view_id': res_id,
                'target': 'new',
                # 'auto_refresh': 1
            })
            print ('----pruinted ir act windoe valsss:>>>>>', vals['ref_ir_act_window'])
            vals['ref_ir_value'] = self.env['ir.defaults'].create({
                'name': button_name,
                'model': src_obj,
                'key2': 'client_action_multi',
                'value':
                    "ir.actions.act_window," + str(vals['ref_ir_act_window']),
                'object': True,
            })
            print ('---printed ir ref defaults :>>>>>>', vals['ref_ir_value'])
        self.write({
            'ref_ir_act_window': vals.get('ref_ir_act_window', False),
            'ref_ir_value': vals.get('ref_ir_value', False),
        })
        return True

    
    def unlink_action(self):
        for template in self:
            try:
                if template.ref_ir_act_window:
                    self.env['ir.actions.act_window'].unlink(template.ref_ir_act_window.id)
                if template.ref_ir_value:
                    ir_values_obj = self.env['ir.values']
                    ir_values_obj.unlink(template.ref_ir_value.id)
            except Exception:
                raise osv.except_osv(
                    ("Warning"), ("Deletion of the action \
                record failed."))
        return True
