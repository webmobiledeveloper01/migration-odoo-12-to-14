from odoo import api, fields, models


class ContractAccount(models.Model):
    _name = 'contract.account'
    _description = "Contract Account"

    name = fields.Char(string='Name', size=64)
    code = fields.Char(string='Code', size=32)


class ContractSubtype(models.Model):
    _name = 'contract.subtype'
    _description = "Contract Sub Type"

    name = fields.Char(string='Name', size=32)


class ContractType(models.Model):
    _name = 'contract.type'
    _description = "Contract Type"

    name = fields.Char(string='Name', size=32)


class PaymentType(models.Model):
    _name = 'payment.type'
    _description = "Payment Type"

    name = fields.Char(string='Name', size=32)
    code = fields.Char(string='Code', size=16)
    requires_day = fields.Boolean(string='Requires Day')


class PricingType(models.Model):
    _name = "pricing.type"
    _description = "Pricing Type"

    name = fields.Char(String='Name', size=128)


class ProofOfUsage(models.Model):
    _name = "proof.of.usage"
    _description = "Proof Of Usage"

    name = fields.Char(String='Name', size=128)


class ResTarrif(models.Model):
    _name = 'res.tariff'
    _description = "Tariff"

    name = fields.Char(string='Code', size=32)
    note = fields.Text(string='Tariff Description')


class ResUplift(models.Model):
    _name = 'res.uplift'
    _description = "Uplift"

    name = fields.Char(string='Name', size=32, )
    uplift_value = fields.Float(string='Uplift Value')
    product_id = fields.Many2one('product.product', string='Product')
    profile_id = fields.Many2one('res.profile', string='Profile')


class ResProfile(models.Model):
    _name = 'res.profile'
    _description = "Profile"

    def name_get(self):
        if not len(self):
            return []
        res = []
        for profile in self:
            p_name = profile.code and '[' + profile.code + '] ' or ''
            p_name += profile.name
            res.append((profile.id, p_name))
        return res

    name = fields.Char(string='Name', size=64)
    code = fields.Char(string='Code', size=8)


class ResRegion(models.Model):
    _name = 'res.region'
    _description = "Region"

    def name_get(self):
        if not len(self):
            return []
        res = []
        for region in self:
            r_name = region.code and '[' + region.code + '] ' or ''
            r_name += region.name
            res.append((region.id, r_name))
            print("$$$$$$$$$$$$$$$$$", res)
        return res

    name = fields.Char(string='Name', size=64)
    code = fields.Char(string='Code', size=8)
    short_name = fields.Char(string='Short Name', size=8)
    postcode_line = fields.One2many(
        'res.postcode', 'region_id', string='Postcode Line')
    region_alias_line = fields.One2many(
        'res.region.alias', 'region_id', string='Alias Name')


class ResPostcode(models.Model):

    _name = 'res.postcode'
    _description = "PostCode"
    _rec_name = 'zip'

    zip = fields.Char(string='Post Code', size=256)
    region_id = fields.Many2one('res.region', string='Region')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    sub_region_id = fields.Many2one('res.sub.region', string='Sub Region(EXZ)')


class ResSubRegion(models.Model):

    _name = 'res.sub.region'
    _description = "Sub Region"
    _rec_name = 'name'

    name = fields.Char(string='EXZ Name', size=32)


class ResRegionAlias(models.Model):

    _name = 'res.region.alias'
    _description = "Region Alias"
    _rec_name = 'name'

    name = fields.Char(string='Name', size=64)
    region_id = fields.Many2one('res.region', 'Region')


class ResProfileRegion(models.Model):
    _name = 'res.profile.region'
    _description = "Profile Region"
    _rec_name = 'mtc_codes'

    region_id = fields.Many2one('res.region', string='Region')
    profile_id = fields.Many2one('res.profile', string='Profile')
    mtc_codes = fields.Char(string='MTC Code', size=3)
    product_id = fields.Many2one('product.product', string='Product')
    amount = fields.Float(string='Amount')
    primary_rate = fields.Float('Primary Rate')
    secondary_rate = fields.Float(string='Secondary Rate')
    tertiary_rate = fields.Float(string='Tertiary Rate')
    amount_p4 = fields.Float(string='Amount')
    primary_rate_p4 = fields.Float(string='Primary Rate')
    secondary_rate_p4 = fields.Float(string='Secondary Rate')
    other_price_1 = fields.Float(string='Other price 1')
    other_price_2 = fields.Float(string='Other price 2')
    llf_code = fields.Char(string='LLF', size=3)
    min_usage = fields.Float(string='Min. Usage')
    max_usage = fields.Float(string='Max. Usage')
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', ondelete='cascade')


class QueryCategory(models.Model):
    _name = 'query.category'
    _description = "Query Category"
    _rec_name = 'name'

    name = fields.Char(string='Name', size=32, required=True)
    code = fields.Char(string='Code', size=16, required=True)
    desc = fields.Text('Description')


class QueryCode(models.Model):
    _name = 'query.code'
    _description = "Query Code"
    _rec_name = 'name'

    name = fields.Char(string='Name', size=256)
    category_id = fields.Many2one('query.category', stirng='Category')
    code = fields.Char(string='Code', size=3, required=True)


class GeneralNote(models.Model):
    _name = 'general.note'
    _description = "General Note"
    _rec_name = 'contract_id'

    query_code_id = fields.Many2one('query.code', string='Query Code')
    name = fields.Text(string='Note', required=True)
    log_date = fields.Datetime(
        string='logging date', readonly=True, default=fields.datetime.now())
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    contract_id = fields.Many2one('res.contract', string='Contract')
    order_id = fields.Many2one('res.contract', string='Sale Order')
    sale_name = fields.Char('Sale Order', related='order_id.sale_name')
    phonecall_id = fields.Many2one('crm.phonecall', string='Phonecall')
    partner_id = fields.Many2one('res.partner', string='Partner')
    check = fields.Boolean(string='Check', default=False)
    create_date_note = fields.Datetime(string='Creation Date')
    create_partner_id = fields.Many2one('res.partner', string='Partner')
    create_contract_id = fields.Many2one('res.contract', string='Contract')
    old_sys_id = fields.Char(string='Old System ID', size=64)

    @api.model
    def default_get(self, fields):
        res = super(GeneralNote, self).default_get(fields)
        res['user_id'] = self.env.uid
        return res


class ResProfileRegionGas(models.Model):
    _name = 'res.profile.region.gas'
    _description = "Profile Region Gas"

    region_id = fields.Many2one('res.region', string='Region')
    product_id = fields.Many2one('product.product', string='Product')
    amount = fields.Float(string='Amount')
    primary_rate = fields.Float(string='Primary Rate')
    min_usage = fields.Float(string='Min. Usage')
    max_usage = fields.Float(string='Max. Usage')
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', ondelete='cascade')
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid To')
    payment_type_id = fields.Many2one('payment.type', string='Payment Type')
    check_sc = fields.Boolean(string='Check Sc')
    sub_region_id = fields.Many2one('res.sub.region', string='Sub Region(EXZ)')
    month = fields.Char(string='Month', size=32)


class UpliftNameReporting(models.Model):
    _name = 'uplift.name.reporting'
    _description = "Uplift Name Reporting"

    name = fields.Char(string='Name', size=128, required=True)
    uplift_value = fields.Float(string='Uplift Value')
    supplier_id = fields.Many2one(
        'res.partner', string='Supplier', required=True)
    utility_type = fields.Selection([('ele', 'Electricity'),
                                     ('gas', 'GAS'),
                                     ('tel', 'Telecoms')], 'Utility Type')
    res_profile_ids = fields.Many2many('res.profile', 'uplift_profile_rel', 'uplift_name_id', 'profile_id',
                                       string='Profiles')
