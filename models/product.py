

import time

from odoo import api, models, fields
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class VerbalText(models.Model):
    _name = 'verbal.text'
    _description = "Verbal Text"
    _rec_name = 'code'

    code = fields.Char(
            'Code', size=8)
    name = fields.Text('Text')
    description = fields.Char(
            'Description', size=128)


class WrittenTemplate(models.Model):
    _name = 'written.template'
    _description = "Written Template"
    _rec_name = 'code'

    code = fields.Char(
            'Code', size=8)
    name = fields.Text('Text')
    description = fields.Char(
            'Description', size=128)


class ElectronicTemplate(models.Model):
    _name = 'electronic.template'
    _description = "Electronic Template"
    _rec_name = 'code'

    code = fields.Char(
            'Code', size=8)
    name = fields.Text(
            'Text', required=True)
    description = fields.Char(
            'Description', size=128)


class ProductProduct(models.Model):

    _inherit = 'product.product'

    uplift_line = fields.One2many('res.uplift', 'product_id', 'Uplift')
    res_profile_region_line = \
    fields.One2many('res.profile.region', 'product_id', 'Profile Region Line')
    via_verbal = fields.Boolean('Verbal Confirmation ?')
    via_written = fields.Boolean('Written Confirmation ?')
    via_electronic = fields.Boolean('Electronic Confirmation ?')
    verbal_text_id = fields.Many2one('verbal.text', 'Verbal Text')
    written_template_id = \
        fields.Many2one('written.template', 'Written Template')
    electronic_template_id = \
        fields.Many2one('electronic.template', 'Electronic Template')

    @api.model
    def create(self, vals):
        user_group_salesteam = self.env.user.has_group('dernetz.group_contract_salesteam')
        # sale_user_group_id = self.env['res.groups'].search(
        #     [('name', '=', 'Contract / Salesteam'), ('users', 'in', [self.uid])])
        if user_group_salesteam:
            raise ValidationError(('Integrity Error!'), (
                "Only Admin Group Users are allowed to create Products!"))

        return super(ProductProduct, self).create(vals)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    verification_logic = fields.Text('Verification Logic')
    verification_req = fields.Boolean('Verification Required')
    option =\
        fields.Selection([('mpan', 'MPAN'), ('other', 'Other')], 'Option')
    call_back_period = fields.Integer('Call Back Period (in Days)')
    product_supplier_line = \
        fields.One2many('product.supplierinfo', 'categ_id', 'Suppliers')
    via_verbal = fields.Boolean('Verbal Confirmation ?')
    via_written = fields.Boolean('Written Confirmation ?')
    via_electronic = fields.Boolean('Electronic Confirmation ?')
    verbal_text_id = fields.Many2one('verbal.text', 'Verbal Text')
    written_template_id = \
        fields.Many2one('written.template', 'Written Template')
    electronic_template_id = \
        fields.Many2one('electronic.template', 'Electronic Template')
    start = fields.Integer('Start (in Days)')
    end = fields.Integer('End (in Days)')
    mid = fields.Integer('Mid')
    alert_line = fields.One2many(
        'alerts',
        'category_id',
        'Alerts',
        help="Arrange alerts sequence in proper ascending order "
        "like 0,1,2,3.\nDon't arrange them like 0,1,3,6 or any \
        other pattern.")
    utility_type = fields.Selection(
        [('ele', 'Electricity'), ('gas', 'GAS'), ('tel', 'Telecoms'), ('wat', 'Water')],
        'Utility Type')
    loa_lead_time = fields.Integer('LOA Lead Time')
    edit_internal_commission = fields.Boolean('Edit Internal Commission')
    edit_broker_commission = fields.Boolean('Edit Broker Commission')
    # 'alert': fields.integer('Alerts (in Days)', size=368),

    # _defaults = {
    #     'verification_logic':
    #     '''result = str(sum(prime * int(digit) for prime, digit in \
    #     zip([3, 5, 7, 13, 17, 19, 23, 29, 31, 37, 41, 43], mpan_code[-13:])) \
    #     % 11 % 10) == mpan_code[-1]''',
    #     'option': 'mpan',
    # }


class Alerts(models.Model):
    _name = 'alerts'
    _description = "Alerts"
    _order = 'sequence'

    name = fields.Integer(
        'Alert', size=3, required=True)
    sequence = fields.Integer('sequence')
    #                'next_call': fields.boolean('Next Call'),
    alert_color = fields.Selection(
        [('black', 'Black'), ('red', 'Red'), ('blue', 'Blue'),
         ('gray', 'Gray'), ('cyan', 'Cyan'), ('darkgreen', 'DarkGreen'), (
             'maroon', 'Maroon'), ('deeppink', 'DeepPink'),
         ('blueviolet', 'BlueViolet')], 'Color', default='black')
    category_id = fields.Many2one('product.category', 'Category')


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    categ_id = fields.Many2one(
        related="product_tmpl_id.categ_id",
        string="Category",
        store=True)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    # def _pricelist_type_get(self):
    #     pricelist_type_obj = self.env['product.pricelist.type']
    #     pricelist_type_ids = pricelist_type_obj.search([], order='name')
    #     pricelist_types = pricelist_type_obj.\
    #         read(pricelist_type_ids, ['key', 'name'])
    #
    #     res = []
    #
    #     for type in pricelist_types:
    #         res.append((type['key'], type['name']))
    #     return res

    # def _get_default_company(self, cr, uid, context=None):
    #     comp = self.pool.get('res.users').browse(cr, uid, uid).company_id
    #     if not comp:
    #         comp_id = self.pool.get('res.company').search(cr, uid, [])[0]
    #         comp = self.pool.get('res.company').browse(cr, uid, comp_id)
    #     return comp.id
    #
    # def _pricelist_active(self, cr, uid, ids, field_name, arg, context=None):
    #     res = {}
    #     for self_obj in self.browse(cr, uid, ids, context=context):
    #         today = time.strftime('%Y-%m-%d')
    #         if self_obj.start_date <= today and self_obj.end_date >= today:
    #             res[self_obj.id] = True
    #         else:
    #             res[self_obj.id] = False
    #     return res
    #
    # def get_active_pricelist(self, cr, uid, context=None):
    #     pricelist_ids = self.search(cr, uid, [], context=context)
    #     if pricelist_ids:
    #         self.write(cr, uid, pricelist_ids, {}, context=context)
    #     return True

    # type = fields.Selection('Pricelist Type') #_pricelist_type_get,
    currency_id = fields.Many2one('res.currency', 'Currency')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    utility_type = fields.Selection(
        [('ele', 'Electricity'), ('gas', 'GAS'), ('tel', 'Telecoms'), ('wat', 'Water')],
        'Utility Type')
    contract_type_id = fields.Many2one(
        'contract.type', 'Contract Type')
    duration = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        'Duration', default='1')
    # active_pricelist = fields.function(
    #     _pricelist_active,
    #     type='boolean',
    #     string='Active',
    #     store=True,
    #     method=True)
    company_id = fields.Many2one('res.company', 'Company')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    res_profile_region_supplier_line = fields.One2many(
        'res.profile.region', 'pricelist_id', 'Profile Region Line')
    res_gas_region_supplier_line = fields.One2many(
        'res.profile.region.gas', 'pricelist_id', 'Gas Region Line')
    # _defaults = {
    #     'duration': '1',
    #     'company_id': _get_default_company,
    # }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
