from odoo import api, fields, models, _
from lxml import etree
import time
from odoo.addons import decimal_precision as dp

POSTAL_ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id',
                         'country_id')
ADDRESS_FIELDS = POSTAL_ADDRESS_FIELDS + \
    ('email', 'phone', 'fax', 'mobile', 'website', 'ref', 'lang')


class CountryState(models.Model):

    _description = "Country state"
    _inherit = 'res.country.state'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        country_obj = self.env['res.country']
        if self._context.get('code') == 'GB':
            country_id = country_obj.search([('code', '=', 'GB')]).ids[0]
            args = args or []
            domain_name = [('country_id', '=', country_id)]
            recs = self.search(domain_name + args, limit=limit)
            return recs.name_get()
        else:
            return super(CountryState, self).name_search()


class ResPartnerTitle(models.Model):
    _inherit = 'res.partner.title'

    require_contact = fields.Boolean('Require Contact')
    company_title = fields.Boolean('Company Title Boolean')


class ResPartnerBank(models.Model):

    """ Bank Accounts """

    _inherit = "res.partner.bank"

    partner_id = fields.Many2one(
            'res.partner', 'Account Owner', ondelete='cascade', select=True)
    bank_check = fields.Boolean('Check')

    # todo
    # def fields_view_get(self,
    #                     cr,
    #                     uid,
    #                     view_id=None,
    #                     view_type=False,
    #                     context=None,
    #                     toolbar=False,
    #                     submenu=False):
    #     sys_admin_user_group_id = self.pool.get('res.groups').search(
    #         cr, uid,
    #         [('name', '=', 'Contract Sysadmin'), ('users', 'in', [uid])])
    #     admin_user_group_id = self.pool.get('res.groups').search(
    #         cr, uid,
    #         [('name', '=', 'Contract / Admin Team'), ('users', 'in', [uid])])
    #     sale_user_group_id = self.pool.get('res.groups').search(
    #         cr, uid,
    #         [('name', '=', 'Contract / Salesteam'), ('users', 'in', [uid])])
    #     if view_type == 'form':
    #         if sys_admin_user_group_id:
    #             view_id = self.pool.get('ir.ui.view').search(
    #                 cr, uid,
    #                 [('name', '=', 'res.partner.bank.form.sys.admin.der')])
    #         if admin_user_group_id:
    #             view_id = self.pool.get('ir.ui.view').search(
    #                 cr, uid,
    #                 [('name', '=', 'res.partner.bank.form.admin.der')])
    #         if sale_user_group_id:
    #             view_id = self.pool.get('ir.ui.view').search(
    #                 cr, uid,
    #                 [('name', '=', 'res.partner.bank.form.saleteam.der')])
    #         if view_id and isinstance(view_id, (list, tuple)):
    #             view_id = view_id[0]
    #     if view_type == 'tree':
    #         if sys_admin_user_group_id:
    #             view_id = self.pool.get('ir.ui.view').search(
    #                 cr, uid,
    #                 [('name', '=', 'res.partner.bank.tree.sys.admin.der')])
    #         if admin_user_group_id:
    #             view_id = self.pool.get('ir.ui.view').search(
    #                 cr, uid,
    #                 [('name', '=', 'res.partner.bank.tree.admin.der')])
    #         if sale_user_group_id:
    #             view_id = self.pool.get('ir.ui.view').search(
    #                 cr, uid,
    #                 [('name', '=', 'res.partner.bank.tree.saleteam.der')])
    #         if view_id and isinstance(view_id, (list, tuple)):
    #             view_id = view_id[0]
    #     res = super(res_partner_bank, self).fields_view_get(
    #         cr,
    #         uid,
    #         view_id=view_id,
    #         view_type=view_type,
    #         context=context,
    #         toolbar=toolbar,
    #         submenu=submenu)
    #     doc = etree.XML(res['arch'])
    #     if view_type == 'search':
    #         for node in doc.xpath("//group[@name='extended filter']"):
    #             doc.remove(node)
    #         res['arch'] = etree.tostring(doc)
    #     return res

    @api.model
    def create(self, vals):
        vals.update({'bank_check': True})
        return super(ResPartnerBank, self).create(vals)


class ElectronicVerification(models.Model):

    _name = 'electronic.verification'
    _description = "Electronic Verification"

    category_id = fields.Many2one(
            'product.category', 'Product Category', required=True)
    contract_type_id = fields.Many2one(
            'contract.type', 'Contract Type', required=True)
    docusign_template_id = fields.Many2one('docusign.template', 'Docusign Template')
    template_id = fields.Many2one('email.template', 'Template')
    type = fields.Selection(
            [('docusign', 'Docusign'), ('verbal', 'Verbal'), ('written',
                                                              'Written')],
            'Method',
            required=True)
    doc_type = fields.Selection(
            [('contract', 'Contract'), ('loa', 'LOA'), ('dd', 'DD')],
            'Document Type')
    company_id = fields.Many2one(
            'res.company', 'Company', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    # defaults = {'type': 'docusign', }


class ElectricPlanInfoLine(models.Model):
    _name = 'electric.plan.info.line'
    _description = "Electric Plan Info Line"

    elec_plan_id = fields.Many2one('res.partner', 'Plans')
    duration = fields.Selection(
            [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
            'Duration')
    plan_type = fields.Selection(
            [('fixed', 'fixed'), ('no s/c', 'no s/c'), ('all inclusive', 'all inclusive'),
             ('fullyfixed', 'fullyfixed'), ('all inclusive & fullyfixed', 'all inclusive & fullyfixed'),
             ('MOP', 'MOP'), ('special', 'special'), ('base', 'base'), ('lowsc', 'lowsc'),
             ('Saturn', 'Saturn'), ('Smart Pay', 'Smart Pay'), ('upfront80', 'upfront80'),
             ('monthly', 'monthly'), ('apr', 'apr'), ('end of curve', 'end of curve')], 'Plan Type')
    uplift_val = fields.Float(
            'Uplift ', digits_compute=dp.get_precision('Uplift Price'))


class GassPlanInfoLine(models.Model):
    _name = 'gass.plan.info.line'
    _description = "Gas Plan Info Line"

    gas_plan_id = fields.Many2one('res.partner', 'Plans1')
    duration = fields.Selection(
            [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
            'Duration')
    plan_type = fields.Selection(
            [('fixed', 'fixed'), ('no s/c', 'no s/c'), ('all inclusive', 'all inclusive'),
             ('fullyfixed', 'fullyfixed'), ('all inclusive & fullyfixed', 'all inclusive & fullyfixed'),
             ('MOP', 'MOP'), ('special', 'special'), ('base', 'base'), ('lowsc', 'lowsc'),
             ('Saturn', 'Saturn'), ('Smart Pay', 'Smart Pay'), ('upfront80', 'upfront80'),
             ('monthly', 'monthly'), ('apr', 'apr'), ('end of curve', 'end of curve')], 'Plan Type')
    uplift_val = fields.Float(
            'Uplift ', digits_compute=dp.get_precision('Uplift Price'))


class TotalSearchLine(models.Model):
    _name = 'total.search.line'
    _description = "Total Search Line"

    user_id = fields.Many2one('res.users', 'Uses')
    date = fields.Date('Date')
    search_user = fields.Integer('Search')


class ElectricInfoLine(models.Model):
    _name = 'electric.info.line'
    _description = "Electric Info Line"
    _rec_name = 'long_mpan'

    partner_id = fields.Many2one('res.partner', string='Partner')
    fuel_type = fields.Char('Fuel Type')
    long_mpan = fields.Char('Long MPAN')
    short_mpan = fields.Char('Short MPAN')
    meter_serial_number = fields.Char('Meter Serial Number')
    meter_type = fields.Char('Meter Type')


class GasInfoLine(models.Model):
    _name = 'gas.info.line'
    _description = "Gas Info Line"
    _rec_name = 'mprn'

    partner_id = fields.Many2one('res.partner', string='Partner')
    fuel_type = fields.Char('Fuel Type')
    mprn = fields.Char('MPRN')
    meter_serial_number = fields.Char('Meter Serial Number')


class ResPartner(models.Model):

    _inherit = 'res.partner'
    _description = 'res.partner'

    
    def updated_partner_domain_script(self):
        for partner in self.browse():
            if partner.parent_id:
                partner.domain = 'contact'
                partner.title = self._context.get('title')
            else:
                partner.domain = 'partner'
                partner.title = self._context.get('title')
        return True

    # def _get_default_company(self, cr, uid, context=None):
    #     if context and context.get('default_parent_id',
    #                                False) and context['default_parent_id']:
    #         company_id = self.browse(
    #             cr, uid, context['default_parent_id'],
    #             context=context).company_id.id
    #         return company_id
    #     company_id = self.pool.get('res.company')._company_default_get(
    #         cr, uid, 'res.partner', context=context)
    #     return company_id
    #

    #
    # def name_get(self, cr, uid, ids, context=None):
    #     if isinstance(ids, (list, tuple)) and not len(ids):
    #         return []
    #     if isinstance(ids, (long, int)):
    #         ids = [ids]
    #     reads = self.read(
    #         cr,
    #         uid,
    #         ids, ['name', 'type', 'parent_id', 'is_company', 'alias',
    #               'is_head_office'],
    #         context=context)
    #     res = []
    #     for record in reads:
    #         name = record['name']
    #         if record['type'] and record['parent_id']:
    #             if record['type'] == 'default':
    #                 type = 'Authorised'
    #             elif record['type'] == 'invoice':
    #                 type = 'Invoice'
    #             elif record['type'] == 'delivery':
    #                 type = 'Shipping'
    #             elif record['type'] == 'contact':
    #                 type = 'Contact'
    #             elif record['type'] == 'other':
    #                 type = 'Other'
    #             else:
    #                 type = ''
    #             name = type and record[
    #                 'name'] + ' ' + '(' + type + ')' or record['name']
    #         if record['is_company'] and record['parent_id']:
    #             alias = record['alias']
    #             name = alias and record[
    #                 'name'] + ' ' + '(' + alias + ')' or record['name']
    #     # if record['is_head_office']:
    #     #    name = record['name']+' '+'(Head Office)'
    #         res.append((record['id'], name))
    #     return res
    #
    # def _display_name_compute(self, cr, uid, ids, name, args, context=None):
    #     context = dict(context or {})
    #     context.pop('show_address', None)
    #     return dict(self.name_get(cr, uid, ids, context=context))
    #
    # _display_name_store_triggers = {
    #     'res.partner': (lambda self, cr, uid, ids,
    #                     context=None: self.search(cr, uid,
    #                                               [('id', 'child_of', ids)]),
    #                     ['parent_id', 'is_company', 'name',
    #                      'alias', 'is_head_office'], 10)
    # }

        # 'display_name': fields.function(_display_name_compute, type='char',
        #                                 string='Name',
        #                                 store=_display_name_store_triggers,
        #                                 select=1),
    contract_line = \
        fields.One2many('res.contract', 'partner_id', 'Contract Line')
    sup_contract_line = \
        fields.One2many('res.contract', 'supplier_id', 'Contract Line')
    question = fields.Char(
        'Security Question', size=256)
    ud_supplier_name = fields.Char(
        'UDCore Supplier Name')
    answer = fields.Char(
        'Security Answer', size=256)
    address_required = fields.Boolean('Addr Required')
    company_number = fields.Char(
        "Company Number", size=24)
    credit_checked = fields.Boolean('Credit Checked')
    credit_score = fields.Char(
        "Credit Score", size=24)
    credit_check_date = fields.Date("Credit Check Date")
    annual_turnover = fields.Char(
        "Annual Turnover", size=24)
    no_of_employees = fields.Char(
        "No. of Employees", size=24)
    micro_business = fields.Boolean('Micro Business')
    county = fields.Char(
        'County', size=64)
    child_ids = fields.One2many(
        'res.partner',
        'parent_id',
        'Contacts',
        domain=[('is_company', '=', False)])
    child_bool = fields.Boolean('Child Bool')
    branch_ids = fields.One2many(
        'res.partner',
        'parent_id',
        'Branch',
        domain=[('is_company', '=', True)])
    past_address = fields.Selection(
        [('current', 'Current Address'), ('past', 'Past Address')],
        'Address Duration',
        required=True)
    years_in_residence = fields.Integer('Years in Residence')
    site_id = fields.Char(
        'Site ID', size=32)
    type = fields.Selection(
        [('default', 'Authorised'), ('invoice', 'Invoice'),
         ('delivery', 'Shipping'), ('contact', 'Contact'),
         ('other', 'Other')], 'Address Type', help="Used to select \
         automatically the right address according to the context in \
         sales and purchases documents.")
    flag = fields.Boolean('Flag')
    street_residence = fields.Char(
        'Street', size=128)
    street2_residence = fields.Char(
        'Street2', size=128)
    zip_residence = fields.Char(
        'Zip', change_default=True, size=24)
    city_residence = fields.Char(
        'City', size=128)
    state_residence_id = fields.Many2one("res.country.state", 'County')
    country_residence_id = fields.Many2one('res.country', 'Country')
    birth_date = fields.Date('DOB')
    general_note = \
        fields.One2many('general.note', 'partner_id', 'General Note')
    alias = fields.Char(
        'Alias', size=256)
    pricelist_line =\
        fields.One2many('product.pricelist', 'partner_id', 'Price Lists')
    check_visibility = fields.Boolean('Visibility')
    product_category_ids = fields.Many2many(
        'product.category', 'product_category_supplier_rel', 'partner_id',
        'category_id', 'Product Type')
    via_verbal = fields.Boolean('Verbal Confirmation ?')
    via_written = fields.Boolean('Written Confirmation ?')
    via_electronic = fields.Boolean('Electronic Confirmation ?')
    verbal_text_id = fields.Many2one('verbal.text', 'Verbal Text')
    written_template_id = \
        fields.Many2one('written.template', 'Written Template')
    electronic_template_id =\
        fields.Many2one('electronic.template', 'Electronic Template')
    utility_type = fields.Selection(
        [('ele', 'Electricity'), ('gas', 'GAS'), ('tel', 'Telecoms'), ('wat', 'Water')],
        'Utility Type')
    company_id = fields.Many2one(
        'res.company', 'Company', select=1)
    verification_line = fields.One2many('electronic.verification',
                                         'partner_id', 'Verification')

    uplift_value = fields.Float(
        'Uplift Value', digits_compute=dp.get_precision('Uplift Price'))
    loa_template = fields.Many2one('docusign.template', 'LOA Template')
    supplier_code = fields.Char(
        'Short Code', size=3)
    payment_type_ids = fields.Many2many(
        'payment.type', 'partner_payment_rel', 'partner_id', 'payment_id',
        'Payment Type')
    webservice_url = fields.Char(
        'Webservices Url', size=256)
    is_head_office = fields.Boolean('Is Head office')
    supplier_commi_confi_line = fields.One2many(
        'supplier.commission.confi', 'supplier_id',
        'Supplier Commission Configuration', ondelete='cascade')
    contract_commi_confi_line = \
        fields.One2many('contract.commission.confi', 'supplier_id',
                        'Contract Commission Configuration', ondelete='cascade')
    dup_id = fields.Integer('Duplicated ID')
    fore = fields.Char('Forename')
    surn = fields.Char('Surname')
    orgn = fields.Char('Organisation')
    search_street = fields.Char('Street')
    search_street2 = fields.Char('Street 2')
    town = fields.Char('Town')
    search_county = fields.Char('County')
    search_zip = fields.Char('GBG Postcode')
    gas_bool = fields.Boolean('Gas')
    electric_bool = fields.Boolean('Electric')
    lguf_bool = fields.Boolean('Large Gas User')
    ctmn = fields.Char('MPRN Count')
    ctmp = fields.Char('MPAN Count')
    electric_info_line = fields.One2many('electric.info.line',
                                          'partner_id',
                                          'Detailed Electric Information')
    gas_info_line = fields.One2many('gas.info.line', 'partner_id',
                                     'Detailed Gas Information')
    old_sys_id = fields.Char('Old System ID', size=64)
    BrokerUpfrontPercentage = fields.Integer('BrokerUpfrontPercentage')
    domain = fields.Char(related='title.name', string="Type")
    # fields for page electric  info line & page gas info line

    supplier_name_elec = fields.Char('Supplier Elec')
    supplier_name_gas = fields.Char('Supplier Gas')
    electric_plans_info_line = fields.One2many('electric.plan.info.line', 'elec_plan_id', 'Plans')
    supplier_typ_elec = fields.Boolean('Electric Supplier')
    supplier_typ_gas = fields.Boolean('Gas Supplier')
    gass_plans_info_line = fields.One2many('gass.plan.info.line', 'gas_plan_id', 'Plans1')
    # 'utili_typ':fields.selection(
    #     [('is_gas_supplier', 'Is Gas Supplier'), ('is_electric_supplier', 'Is Electric Supplier')],'Utility Type'),

    @api.model
    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        uk_id = self.env['res.country'].search([('code', '=', 'GB')])
        print ("--print uk id ::>>>>", uk_id)
        if uk_id:
            res.update({'country_id': uk_id.id})
        if res.get('child_bool'):
            res['is_company'] = False
            # print ('--in default get method if context child bool :::>>>', res.get('child_bool'))
        else:
            res['is_company'] = True
            # print ('--print child bool in else in default get method', res.get('child_bool'))
        res['past_address'] = 'current'
        res['type'] = ''
        res['check_visibility'] = True
        return res

    # @api.depends('child_bool')
    # def is_company_child_bool(self):
    #     for rec in self:
    #         print ('---print rec child bool::>>>', rec.child_bool)
    #         if rec.child_bool:
    #             rec.is_company = False
    #             print ('printed in if condition :::>>>', rec.is_company)
    #         else:
    #             rec.is_company = True
    #             print ('printed in else condition :::>>>>>', rec.is_company)

    
    def _check_title(self):
        for partner in self:
            if partner.title and partner.title.require_contact:
                if len(partner.child_ids) == 0:
                    return False
        return True

    
    def _check_childs(self):
        for partner in self:
            address_type = []
            for child in partner.child_ids:
                address_type.append(child.type)
                if address_type.count('default') > 1:
                    return False
        return True

    
    def _check_year_in_resident(self):
        for partner in self:
            for child in partner.child_ids:
                if child.years_in_residence > 99 or \
                        child.years_in_residence < 0:
                    return False
        return True

    
    def _check_broke_up_front_percentage(self):
        for partner in self:
            if partner.BrokerUpfrontPercentage > 100 or partner.BrokerUpfrontPercentage < 0:
                return False
        return True

    _constraints = [
        (_check_title,
         '\n\nError !\n\nPartner with Selected Title must have atleast'
         'one contact.\n\nPlease Create atleast One Authorised Contact for \
         the Partner',
         ['title', 'child_ids']),
        (_check_childs,
         '\nError !\n\nThere cannot be more than one contact of \
         type "Authorised"',
         ['child_ids']),
        (_check_year_in_resident, '\nError !\n\nThere cannot be more than 99',
         ['years_in_residence']),
        (_check_broke_up_front_percentage,
         '\nError !\n\n You must be set value between 0 to 100',
         ['BrokerUpfrontPercentage']),
    ]

    # @api.onchange('visibility')
    # def onchange_visibility(self):
    #     if visibility:
    #         for self_obj in self:
    #             if self_obj.child_ids:
    #                 self.write({'check_visibility': True})
    #     else:
    #         for self_obj in self:
    #             if self_obj.child_ids:
    #                 self.write({'check_visibility': False})
    #
    # def search(self, cr, uid, args, offset=0, limit=None, order=None,
    #            context=None, count=False):
    #     if context is None:
    #         context = {}
    #     if 'partner_bank_click' in context:
    #         if context.get('partner_bank_click', False):
    #             child_serach = self.pool.get('res.partner').search(
    #                 cr, uid, [('parent_id', '=',
    #                            context['partner_bank_click'])])
    #             args = [
    #                 ('id', 'in',
    #                  child_serach + [context['partner_bank_click']])
    #             ]
    #         else:
    #             args = [('id', 'in', [])]
    #     sys_admin_user_group_id = self.pool.get('res.groups').search(
    #         cr, uid, [('name', '=', 'Contract Sysadmin'),
    #                   ('users', 'in', [uid])])
    #     if not sys_admin_user_group_id:
    #         args = [['check_visibility', '=', True]] + args
    #     return super(res_partner, self).search(cr, uid, args=args,
    #                                            offset=offset, limit=limit,
    #                                            order=order, context=context,
    #                                            count=count)
    #
    # def create(self, vals):
    # ctx_temp = context.copy()
    # ctx_temp.update({'default_create_date_note':
    #                  time.strftime('%%Y-%%m-%%d %%H:%%M:%%S')})
    # sysadmin_grp = self.pool.get('res.users').has_group(
    #     cr, uid, 'dernetz.group_contract_sys_admin')
    # if 'supplier' in vals and vals['supplier'] and not sysadmin_grp:
    #     raise osv.except_osv(('Insufficient Rights!'), (
    #         "Please contact your system administrator to create \
    #         a supplier."
    #     ))
    # vals.update({'company_type': 'company'})
    # return super(res_partner, self).create(vals)
    #
    # def write(self, cr, uid, ids, vals, context={}):
    #     temp_ctx = context.copy()
    #     temp_ctx.update({'default_create_date_note':
    #                      time.strftime('%Y-%m-%d %H:%M:%S')})
    #     return super(res_partner, self).write(
    #         cr, SUPERUSER_ID, ids, vals, context=temp_ctx)
    #
    # def onchange_years_in_resident(self, cr, uid, ids, years, context=None):
    #     res = {'flag': False}
    #     warning = ''
    #     if not years:
    #         return {'value': res}
    #     if years <= 3:
    #         res.update({'flag': True})
    #     else:
    #         warn_msg = 'To create Past Address Years In Residence must be \
    #         less then 3!'
    #         warning = {'title': 'Warning !', 'message': warn_msg}
    #     return {'value': res, 'warning': warning}
    #
    # def onchange_address(self, cr, uid, ids, use_parent_address, parent_id,
    #                      context=None):
    #     parent_id = context.get('default_parent_id', False)
    #
    #     def value_or_id(val):
    #         """ return val or val.id if val is a browse record """
    #         return val if isinstance(val, (bool, int, long, float,
    #                                        basestring)) else val.id
    #     result = {}
    #     if parent_id:
    #         if ids:
    #             partner = self.browse(cr, uid, ids[0], context=context)
    #             if partner.parent_id and partner.parent_id.id != parent_id:
    #                 result['warning'] = \
    #                     {'title': _('Warning'),
    #                      'message': _('Changing the company of a contact \
    #                      should only be done if it was never correctly set. \
    #                      If an existing contact starts working for a new \
    #                      company then a new contact should be created under \
    #                      that new company. You can use the "Discard" button \
    #                      to abandon this change.')}
    #         if use_parent_address:
    #             parent = self.browse(cr, uid, parent_id, context=context)
    #             address_fields = self._address_fields(cr, uid, context=context)
    #             result['value'] = dict((key, value_or_id(parent[key])) for
    #                                    key in address_fields)
    #     else:
    #         result['value'] = {'use_parent_address': False}
    #     return result
    #
    @api.onchange('title')
    def onchange_title(self):
        if self.title:
            return {'value': {'address_required': True}}
        else:
            return {'value': {'address_required': False}}

        # and self.env['res.partner.title'].browse(title.require_contact)
