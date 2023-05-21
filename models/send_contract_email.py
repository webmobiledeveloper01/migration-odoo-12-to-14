from odoo import api, fields, models


class SendContractEmail(models.Model):
    _name = "send.contract.email"
    _description = "Send Contract Email"

    name = fields.Char(string='Name', size=32, required=True)
    state = fields.Selection([('draft', 'Draft'), ('doc_pending', 'Pending(Admin)'),
                              ('docusign_pending',
                               'Delivered(Docusign)'), ('sale_agreed', 'Sale Confirmed'),
                              ('confirmed', 'Admin Confirmed'), ('accepted',
                                                                 'Supplier Accepted'),
                              ('complete', 'LiveNocis'), ('payment_confirmed',
                                                          'Payment Confirmed'),
                              ('query', 'Sales Query'), ('admin_query', 'Admin Query'),
                              ('cot_cancelled', 'COT Cancelled'), ('cancelled', 'Cancelled')],
                             string='State', required=True)
    supplier_line = fields.One2many(
        'res.supplier.template', 'send_contract_email_id', 'Supplier')


class ResSupplierTemplate(models.Model):

    _name = 'res.supplier.template'
    _description = "Res Supplier Template"

    send_contract_email_id = fields.Many2one(
        'send.contract.email', string='Send contract Email')
    partner_id = fields.Many2one('res.partner', string='Supplier')
    template_line = fields.One2many(
        'contract.email.template', 'res_supplier_template_id', string='Template')


class ContractEmailTemplate(models.Model):

    _name = 'contract.email.template'
    _description = "Contract Email Template"

    name = fields.Char(string='Name', size=32, required=True)
    template_id = fields.Many2one(
        'mail.template', string='Template', required=True)
    once_check = fields.Boolean(string='Send Once ?')
    res_supplier_template_id = fields.Many2one(
        'res.supplier.template', string='Send Contract Email')


class ContractSendEmailHistory(models.Model):

    _name = 'contract.send.email.history'
    _description = "Contract Send Email History"

    name = fields.Char(string='Name', size=32)
    date = fields.Datetime('Datetime')
    state_from = fields.Selection([('draft', 'Draft'), ('doc_pending', 'Pending(Admin)'),
                                   ('docusign_pending', 'Delivered(Docusign)'), (
                                       'sale_agreed', 'Sale Confirmed'),
                                   ('confirmed', 'Admin Confirmed'), ('accepted',
                                                                      'Supplier Accepted'),
                                   ('live', 'LIVE'), ('complete', 'LiveNocis'),
                                   ('livenocis_scanned', 'LiveNOCIS Scanned'),
                                   ('payment_confirmed',
                                    'Payment Confirmed'), ('query', 'Sales Query'),
                                   ('admin_query', 'Admin Query'), ('cot_cancelled',
                                                                    'COT Cancelled'),
                                   ('cancelled', 'Cancelled')], string='From State', required=True)
    state_to = fields.Selection([('draft', 'Draft'), ('doc_pending', 'Pending(Admin)'),
                                 ('docusign_pending', 'Delivered(Docusign)'),
                                 ('sale_agreed', 'Sale Confirmed'), ('confirmed',
                                                                     'Admin Confirmed'),
                                 ('accepted', 'Supplier Accepted'), ('live',
                                                                     'LIVE'), ('complete', 'LiveNocis'),
                                 ('livenocis_scanned', 'LiveNOCIS Scanned'), (
                                     'payment_confirmed', 'Payment Confirmed'),
                                 ('query', 'Sales Query'), ('admin_query',
                                                            'Admin Query'),
                                 ('cot_cancelled', 'COT Cancelled'), ('cancelled', 'Cancelled')],
                                string='To State', required=True)
    contract_id = fields.Many2one('res.contract', 'Contract ID')
    write_uid = fields.Many2one("res.users", string="Last Updated By")
