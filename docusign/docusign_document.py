from odoo import api, fields, models
from odoo.osv import osv
import base64
import tempfile
import json
import logging
import shutil
import time
from datetime import datetime
from odoo.exceptions import ValidationError
# from odoo import SUPERUSER_ID
from odoo import netsvc
from odoo.addons.dernetz.docusign import docusign_config
_logger = logging.getLogger(__name__)


class DocusignDocument(models.Model):

    _name = 'docusign.document'
    _rec_name = 'subject'
    _inherit = ['mail.thread']
    _description = "Docusign Document"

    mail_server_id = fields.Many2one('docusign.config', string='Outgoing mail server',
                                     states={'draft': [('readonly', False)]}, default=1)
    auto_delete = fields.Boolean(string='Auto Delete',
                                 help="Permanently delete this email after sending it, \ to save space",
                                 states={'draft': [('readonly', False)]})
    references = fields.Text(string='References', help='Message references, such as identifiers of \ previous messages',
                             states={'draft': [('readonly', False)]})
    subject = fields.Char(string='Subject', states={'draft': [('readonly', False)]})
    email_from = fields.Char(string='From', help='Message sender, taken from user preferences.',
                             states={'draft': [('readonly', False)]})
    email_to = fields.Text(string='To', help='Message recipients', states={'draft': [('readonly', False)]})
    email_cc = fields.Char(string='Cc', help='Carbon copy message recipients', states={'draft': [('readonly', False)]})
    reply_to = fields.Char(string='Reply-To', help='Preferred response address for the message',
                           states={'draft': [('readonly', False)]})
    body_html = fields.Text(string='Rich-text Contents', help="Rich-text/HTML message",
                            states={'draft': [('readonly', False)]})
    date = fields.Datetime(string='Date Created', states={'draft': [('readonly', False)]})
    signhere_tab = fields.Char('Signhere Tab', size=128, states={'draft': [('readonly', False)]})
    model = fields.Char(string='Related Document Model', size=128, select=1, states={'draft': [('readonly', False)]})
    message_id = fields.Char(string='Message-Id', help='Message unique identifier', select=1,
                             states={'draft': [('readonly', False)]})
    author_id = fields.Many2one('res.users', string='Author', select=1, ondelete='set null',
                                help="Author of the message. If not set, email_from \ "
                                "may hold an email address that did not match any partner.",
                                states={'draft': [('readonly', False)]})
    partner_ids = fields.Many2many('res.partner', 'docusign_email_res_partner_rel', 'document_id', 'partner_id',
                                   string='Additional contacts', states={'draft': [('readonly', False)]})
    attachment_ids = fields.Many2many('ir.attachment', 'docusign_email_ir_attachments_rel', 'document_id',
                                      'attachment_id', string='Attachments', states={'draft': [('readonly', False)]})
    sign_attachment_ids = \
        fields.Many2many('ir.attachment', 'docusign_email_ir_sign_attachments_rel', 'sign_document_id',
                                           'sign_attachment_id', string='Attachments',
                         states={'draft': [('readonly', False)]})
    res_id = fields.Integer(string='Related Document ID', select=1, states={'draft': [('readonly', False)]})

    docusign_template_id = fields.Many2one('docusign.template', 'Docusign Template')
    # states={'draft': [('readonly', False)]}
    ref_id = fields.Integer('RefID', states={'draft': [('readonly', False)]})
    env_id = fields.Char(string='Envelope Id', size=256, states={'draft': [('readonly', False)]})
    notification = fields.Boolean(string='Is Notification', states={'draft': [('readonly', False)]})
    contract_id = fields.Many2one('res.contract', string='Contract')
    state = fields.Selection([('draft', 'Draft'), ('sent', 'Sent'),
                              ('delivered', 'Delivered'), ('signed', 'Signed'),
                              ('completed', 'Completed'), ('declined', 'Declined'),
                              ('deleted', 'Deleted'), ('voided', 'Voided'),
                              ('fail', 'Failed'), ('cancel', 'Cancelled'),
                              ('admin_cancel', 'Admin Cancelled'),
                              ('admin_delete', 'Admin Deleted')], 'Status')
    # track_visibility='onchange'),
    partner_id = fields.Many2one('res.partner', string='Partner')

    
    def send_document_cron_btn(self):
        for rec in self:
            file_lst = []
            if rec.state not in ['draft', 'fail']:
                raise ValidationError("Invalid Data You must select the \
                email which is in Draft or Fail state.")
                # raise osv.except_osv(('Invalid Data!'), ("You must select the \
                # email which is in Draft or Fail state."))
            login = {
                'baseurl': rec.mail_server_id.docusign_baseurl,
                'auth_str': rec.mail_server_id.docusign_authstr
            }
            print ('----base url printed ::>>>>', login['baseurl'])
            print ('----base url printed ::>>>>', login['auth_str'])
            print ('print attachments ids ', rec.attachment_ids)
            files = [attach for attach in rec.attachment_ids]
            print ('---print files ::::>>>', files)
            for f in files:
                # content = base64.b64decode(f.datas)
                content = f.datas
                content = content.decode("utf-8")
                # content = content.decode('unicode_escape').encode('utf-8')
                # print ('----printed after decode string:::>>>>>', content)
                directory_name = tempfile.mkdtemp()
                print ('---print file name :::>>>>', f.name)
                filename = directory_name + "/%s" % f.name
                file_lst.append(filename)
                file = open(filename, 'w')
                file.write(content)
                file.close()
            print('----parinted partner ids:::>>>>', rec.partner_ids)
            print ('--print file lst :::>>>>>>>', file_lst)
            recipient = [partner for partner in rec.partner_ids][0]
            body = rec.body_html
            subject = rec.subject
            signature = rec.docusign_template_id and \
                        rec.docusign_template_id.signhere_tab
            xoff = rec.docusign_template_id and \
                   rec.docusign_template_id.xoff
            yoff = rec.docusign_template_id and \
                   rec.docusign_template_id.yoff
            datesigned = rec.docusign_template_id and \
                         rec.docusign_template_id.signhere_tab_date or False
            xoff_date = rec.docusign_template_id and \
                        rec.docusign_template_id.xoff_date or 0.00
            yoff_date = rec.docusign_template_id and \
                        rec.docusign_template_id.yoff_date or 0.00
            _logger.info(
                ("__________docusign__mail_id___________ %s") % (rec))
            print ('---printed docusign config ::>>>>', docusign_config)
            print ('---login:::>>', login)
            print ('---reciepeint ::>>', recipient)
            print ('---body--::>>>', body)
            print ('---subject---::>>>', subject)
            print ('---file list:--::>>>', file_lst)
            print ('---signature----::>>', signature)
            print ('----xoff::>>>>', xoff)
            print ('---xoff::>>>', yoff)
            print ('---datesigned::>>>', datesigned)
            print ('---xoffdate ---:>>>>', xoff_date)
            print ('----yoff date ::>>>>>', yoff_date)
            response, content = docusign_config.create_envelope(
                self, login, recipient, body, subject, file_lst, signature,
                xoff, yoff, datesigned, xoff_date, yoff_date)
            print ("----printed response ::>>>>", response)
            print ("----printed content ::>>>>>>", content)
            _logger.info(
                ("____docusign__response____________ %s") % (response))
            _logger.info(("____docusign__content____________ %s") % (content))
            content = json.loads(content.decode('utf-8'))
            # print ('---content printed::>>>>>>',content)
            # print ('----response printed:::>>>>>',response)
            msg = ("Envelope successfully sent to <b>%s</b> of this <b>%s</b> \
            email id.") % (recipient.name, recipient.email)
            if response.get('status') != '201':
                msg = ("<b>%s</b> : %s.") % (content.get('errorCode'),
                                             content.get('message'))
                rec.write({
                    'state': 'fail'
                })
            else:
                rec.write({
                    'state': 'sent',
                    'env_id': content.get('envelopeId'),
                })
                if rec.model == 'res.contract':
                    contract_id = self.env['res.contract'].sudo().search([('id', '=', rec.res_id)])
                    contract_id.write({
                        'state': 'docusign_pending'
                    })
                elif rec.model == 'sale.order':
                    # print "-----elif sale order::>>>>"
                    sale_order_id = self.env['sale.order'].sudo().search([('id', '=', rec.res_id)])
                    sale_order_id.write({
                        'document_sent_date': datetime.now()
                    })
            rec.message_post(body=msg)
            # Clean up the directory yourself
            shutil.rmtree(directory_name)
        return True

    
    def download_document_cron_btn(self):
        for email_id in self:
            attach_ids = []
            if email_id.state not in ['sent', 'delivered'] and \
                    email_id.env_id != '':
                raise osv.except_osv(('Invalid Data!'), (
                    "You must select the email which is in Sent or \
                    Delivered state."))
            # print '-------print model_________::::::::::::::::::::',email_id.model
            if email_id.model == 'sale.order':
                # print '-------Within if statement__)(::::::::::::::::::::', email_id.model
                res_ids = self.env[email_id.model].sudo().search([('id', '=', email_id.res_id)])
                if not res_ids:
                    _logger.warning((" Related record does not exist or has been \
                    deleted from the system. model %s & \
                    Id %s") % (email_id.model, email_id.res_id))
                    msg = (" Related record does not exist or has been deleted \
                    from the system. model %s & Id %s") % (email_id.model,
                                                           email_id.res_id)
                    self.message_post(body=msg)
                    self.write({
                            'state': 'cancel'
                        })
                    return True
                login = {
                    'baseurl': email_id.mail_server_id.docusign_baseurl,
                    'auth_str': email_id.mail_server_id.docusign_authstr
                }
                envid = email_id.env_id
                response_status, content_status = docusign_config \
                    .req_env_status_url(self, login, envid)
                # print ('---printed cpntent status::>>>>>>',content_status)
                status_with_content = content_status.decode('utf-8')
                # print ('----printed dcontenty wityh syatus::>>>>',status_with_content)
                content_status = json.loads(status_with_content)
                if response_status.get('status') != '200':
                    msg = ("<b>%s</b> : %s.") % (content_status.get('errorCode'),
                                                 content_status.get('message'))
                    self.message_post(body=msg)
                if content_status.get('status') == 'completed':
                    req_info = "/envelopes/" + email_id.env_id
                    response_doc, file_lst, dir_lst = docusign_config \
                        .download_documents(self, login, req_info)
                    if response_doc.get('status') != '200':
                        msg = "Unable to retrive documents from Docusign."
                        self.message_post(body=msg)
                    else:
                        sale_order_obj = self.env['sale.order'].sudo().search([('id', '=', email_id.res_id)])
                        # print ('---sale order object printed ::>>>>>',sale_order_obj)
                        # sale_obj_browse = self.pool.get('sale.order').browse(sale_order_obj)
                        for filename in file_lst:
                            file_name = "doc.pdf"
                            f_name = filename.split('/')
                            if email_id.model == 'res.contract':
                                file_name = f_name and f_name[-1] or str(
                                    email_id.res_id) + "_doc.pdf"
                            elif email_id.model == 'sale.order':
                                f_name = f_name[-1].split('.')
                                file_name = f_name and f_name[0] + ' - ' + \
                                    time.strftime('%Y-%m-%d') + ".pdf" or \
                                    str(email_id.res_id) + "_doc.pdf"
                            elif email_id.model == 'res.partner':
                                file_name = "Customer LOA - " + \
                                    time.strftime('%Y-%m-%d') + ".pdf"
                            filecontents = open(filename, "rb").read()
                            filecontents_en = filecontents.decode("utf-8")
                            data_attach = {
                                'name': file_name,
                                'datas': filecontents_en,
                                'datas_fname': file_name,
                                'res_model': email_id.model,
                                'res_id': email_id.res_id,
                                'type': 'binary',
                            }
                            res_id = self.env['ir.attachment'].sudo().create(data_attach)
                            attach_ids.append(res_id.id)
                            # print ('---printed attach ments ids::>>>>>',attach_ids)
                        email_id.write(
                            {'sign_attachment_ids': [(6, 0, attach_ids)]}
                        )
                        if sale_order_obj:
                            sale_message = [self.env['mail.message'].create(
                                {'body': 'Signed LOA Received',
                                 'model': 'sale.order', 'res_id': int(sale_order_obj)}
                            )]
                            sale_order_obj.write({'document_received_date': datetime.now()})
                            # print "----received date time::>>>>",sale_obj_browse.document_received_date
                            # {sale_obj_browse.message_ids:[(0,0, 'LOA Signed and recieved')]}
                            # print '----message_ids:::::::;',sale_obj_browse.message_ids

                        if email_id.model == 'res.contract':
                            contract_id = self.env['res.contract'].sudo().search([('id', '=', email_id.res_id)])
                            contract_id.write({
                                'state': 'sale_agreed'
                            })
                        query_id = self.env['query.code'].sudo().search([('name', '=', 'Docusign')])
                        if not query_id:
                            query_id = self.env['query.code'].sudo().create({
                                'name': 'Docusign',
                                'code': '29'}
                            )
                        con_browse = self.env['res.contract'].sudo().search([('id', '=', email_id.res_id)])
                        note_vals = {
                            'query_code_id': query_id and query_id.id or False,
                            'user_id': email_id.author_id and
                            email_id.author_id.id or False,
                            'partner_id': email_id.partner_id and
                            email_id.partner_id.id or False,
                            'name': 'Completed',
                            'contract_id': email_id.model == 'res.contract' and
                            email_id.res_id or False
                        }
                        self.env['general.note'].sudo().create(note_vals)
                        for dir in dir_lst:
                            shutil.rmtree(dir)
                if content_status.get('status') == 'declined':
                    response_dec_status, content_dec_status = docusign_config \
                        .req_decline_env_status(self, login, envid)
                    content_dec_status = json.loads(content_dec_status)
                    if response_dec_status.get('status') != '200':
                        msg = ("<b>%s</b> : %s.") % \
                            (content_dec_status.get('errorCode'),
                             content_dec_status.get('message'))
                        self.message_post(body=msg)
                    query_id = self.env['query.code'].sudo().search([('name', '=', 'Docusign Declined')])
                    if not query_id:
                        query_id = [self.env['query.code'].sudo().create({
                            'name': 'Docusign Declined',
                            'code': '28'}
                        )]
                    con_browse = self.env['res.contract'].sudo().search([('id', '=', email_id.res_id)])
                    decline_reason = content_dec_status.get('signers', False) and \
                        content_dec_status['signers'][0] \
                        .get('declinedReason', False) and \
                        content_dec_status['signers'][0]['declinedReason'] or \
                        'Docusign Declined',
                    if isinstance(decline_reason, tuple):
                        decline_reason = decline_reason[0]
                    note_vals = {
                        'query_code_id': query_id and query_id.id or False,
                        'user_id': email_id.author_id and email_id.author_id.id or
                        False,
                        'partner_id': con_browse.partner_id and
                        con_browse.partner_id.id or False,
                        'name': decline_reason,
                        'contract_id': email_id.model == 'res.contract' and
                        email_id.res_id or False
                    }
                    self.pool.get('general.note').sudo().create(note_vals)
                self.write({
                    'state': content_status.get('status')
                })
        return True

    
    def cancel_document(self):
        for rec in self:
            if rec.model == 'res.contract':
                if rec.contract_id or rec.res_id:
                    self.env['res.contract'].action_cancel([rec.contract_id.id])
            else:
                self.write({
                        'state': 'cancel'
                    })
        return True

    
    def cron_docusign_alerts(self):
        docusign_sent_email_ids = self.search([('state', 'in', ('sent', 'delivered')), ('env_id', '!=', '')])
        if docusign_sent_email_ids:
            self.download_document_cron_btn(docusign_sent_email_ids)
        return True
