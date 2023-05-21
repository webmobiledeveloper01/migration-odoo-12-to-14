from odoo import api, fields, models
from odoo import exceptions, _
import re


class MeterDataLine(models.Model):
    _name = 'meter.data.line'
    _description = "Meter Data Line"

    def calculate_sellrate(self):
        for meter_data_line in self:
            if meter_data_line.standing_charge == 0:
                meter_data_line.write({"primary_rate": 0,
                                       "secondary_rate": 0,
                                       "tertiary_rate": 0,
                                       'uplift_id': False,
                                       'commission': 0.0})
        return True

    @api.depends("commission")
    def _get_commission(self):
        for rec in self:
            if rec.contract_id:
                print('--contract id printed in if condition ::>>>>>',
                      rec.contract_id)
                if rec.co_boolean and rec.so_boolean:
                    if int(rec.contract_id.year_duration) > 0:
                        com = (rec.product_uom_qty * rec.uplift_value *
                               int(rec.contract_id.year_duration))
                        print('--print com in if condition ::>>> ::>>>>>', com)
                        rec.commission = com != 0 and (com / 100) or 0.00
                        print('---print rec commission', rec.commission)
                elif rec.so_boolean and not rec.co_boolean:
                    if int(rec.contract_id.sale_year_duration) > 0:
                        com = (rec.product_uom_qty * rec.uplift_value *
                               int(rec.contract_id.sale_year_duration))
                        print('---print in elif condition ', com)
                        rec.commission = com != 0 and (com / 100) or 0.00
                else:
                    if int(rec.contract_id.sale_year_duration) > 0:
                        com = (rec.product_uom_qty * rec.uplift_value *
                               int(rec.contract_id.sale_year_duration))
                        print('---print com in else condition :::>>>>', com)
                        rec.commission = com != 0 and (com / 100) or 0.00

    # @api.constrains('main_meter')
    # def _check_main_line(self):
    #     for line in self:
    #         order_line_id = line.sale_order_line_id.id
    #         mld_ids = self.search([('sale_order_line_id', '=', order_line_id)])
    #         mld_ids = list(set(mld_ids) - set(self.ids))
    #         if mld_ids:
    #             for mld_obj in self:
    #                 if line.main_meter and mld_obj.main_meter:
    #                     return False
    #     return True
    #
    # @api.constrains('region_id')
    # def _check_all_region(self):
    #     for line in self:
    #         order_line_id = line.sale_order_line_id.id
    #         if order_line_id:
    #             mld_ids = self.search([('sale_order_line_id', '=', order_line_id)])
    #             mld_ids = list(set(mld_ids) - set(self.ids))
    #             if mld_ids:
    #                 for mld_obj in self:
    #                     if line.region_id and (line.region_id.id != mld_obj.region_id.id):
    #                         return False
    #     return True
    #
    #
    # @api.constrains('mpan_code')
    # def _check_duplicate_mpan_code(self):
    #     for line in self:
    #         if line.contract_id and line.contract_id.renew_check:
    #             return True
    #         order_line_id = line.sale_order_line_id.id
    #         if order_line_id:
    #             mld_ids = self.search([('sale_order_line_id', '=', order_line_id)])
    #             mld_ids = list(set(mld_ids) - set(self.ids))
    #             if mld_ids:
    #                 for mld_obj in self:
    #                     if line.mpan_code and (line.mpan_code == mld_obj.mpan_code):
    #                         reg_exp = re.compile('[^0-9]*')
    #                         line_mpan_code = reg_exp.sub('', line.mpan_code)
    #                         mld_mpan_code = reg_exp.sub('', mld_obj.mpan_code)
    #                         if line_mpan_code == "000000000000000000000" and \
    #                             mld_mpan_code == "000000000000000000000":
    #                             return True
    #                         elif line_mpan_code == mld_mpan_code:
    #                             return False
    #     return True

    # update_rates_button = fields.Char(string='UpDate Rates')
    contract_button = fields.Integer(
        compute="_compute_contract_button", string="Contract")

    contract_id = fields.Many2one('res.contract', string='Contract')
    partner_id = fields.Many2one('res.partner', string='Partner')
    sale_name = fields.Char('Sale Order', related='contract_id.sale_name')

    name = fields.Char(string="Code")
    electric_info_line_id = fields.Many2one(
        'electric.info.line', string="MPAN From Register")
    mpan_code = fields.Char(string='MPAN Code')

    gas_info_line_id = fields.Many2one(
        'gas.info.line', string='MPR From Register')
    mpr_code = fields.Char(string='MPR')
    gas_bool = fields.Boolean('Gas')
    electricity_bool = fields.Boolean('Electricity')

    clear_all = fields.Boolean(string='Clear All', help="If you click clear all then whenever you change the usage \
                it will clear all data")
    product_id = fields.Many2one('product.product', string='Product')
    capacity = fields.Float(string='Capacity')
    profile_id = fields.Many2one('res.profile', string='Profile')
    check_sc = fields.Boolean(string='Check SC/Non-SC')
    check_use_baserate = fields.Boolean(string='Use Base_Rate Pricing')
    supplier_name = fields.Char(string='Supplier')
    uplift_dummy = fields.Float(
        string="UpLift Value")  # 'sale_order_line_id','uplift_value',type='float',
    # string='Uplift Value',digits_compute=dp.get_precision('Product Price')

    product_uom_qty = fields.Float(string='Usage')
    region_id = fields.Many2one("res.region", string='Region')
    mtc_code = fields.Char(string='MTC Code')
    uplift_value = fields.Float(string='UpLift Value')

    standing_charge = fields.Float(string='Standing Charge', digits=(14, 5))
    primary_rate = fields.Float(string='Primary Rate', digits=(14, 5))
    secondary_rate = fields.Float(string='Secondary Rate', digits=(14, 5))
    tertiary_rate = fields.Float(string='Tertiary Rate', digits=(14, 5))
    other_price_1 = fields.Float(string='Other price 1', digits=(14, 5))
    other_price_2 = fields.Float(string='Other price 2', digits=(14, 5))
    fit_rate = fields.Float(string='FIT Rate', digits=(14, 5))
    kva_charge = fields.Float(string='KVA', digits=(14, 5))

    standing_charge_sell = fields.Float(
        string='Standing Sell Charge', digits=(14, 5))
    primary_rate_sell = fields.Float(
        string='Primary Sell Rate', digits=(14, 5))
    secondary_rate_sell = fields.Float(
        string='Secondary Sell Rate', digits=(14, 5))
    tertiary_rate_sell = fields.Float(
        string='Tertiary Sell Rate', digits=(14, 5))
    other_price_1_sell = fields.Float(
        string='Sell Rate 1', compute="other_price_1_rate_compute", digits=(14, 5))
    other_price_2_sell = fields.Float(
        string='Sell Rate 2', compute="other_price_2_rate_compute", digits=(14, 5))
    fit_rate_sell = fields.Float(
        compute="fit_rate_compute", string='FIT Rate Sell', digits=(14, 5))
    kva_charge_sell = fields.Float(string='KVA', digits=(14, 5))

    main_meter = fields.Boolean(string='Main?')

    commission = fields.Float(string='Commission', compute="_get_commission")
    serial_number = fields.Char(string='Serial Number')
    measurement_class = fields.Char(string='Serial Number')
    meter_read = fields.Integer(stirng='Meter Read')
    meter_read_date = fields.Date(string='Meter Read Date')
    renew_check = fields.Boolean(string='Renewed Meter Data Line')

    standing_charge_sell_dummy = fields.Float(
        string='Standing Sell Charge', digits=(14, 5))
    primary_rate_sell_dummy = fields.Float(
        string='Primary Sell Rate', digits=(14, 5))
    secondary_rate_sell_dummy = fields.Float(
        strng='Secondary Sell Rate', digits=(14, 5))
    tertiary_rate_sell_dummy = fields.Float(
        stirng='Tertiary Sell Rate', digits=(14, 5))
    other_price_1_sell_dummy = fields.Float(
        stirng='Sell Rate 1', compute="other_price_1_rate_compute", digits=(14, 5))
    other_price_2_sell_dummy = fields.Float(
        string='Sell Rate 2', compute="other_price_2_rate_compute", digits=(14, 5))
    fit_rate_sell_dummy = fields.Float(
        string='FIT Rate sell', compute='fit_rate_compute', digits=(14, 5))
    supplier = fields.Char('Supplier')
    utility_type = fields.Selection([('ele', 'Electricity'), ('gas', 'GAS'), ('tel', 'Telecoms'), ('wat', 'Water')],
                                    string='Utility Type', compute='get_so_co_boolean_contract')
    co_boolean = fields.Boolean(
        "Co Boolean", compute='get_so_co_boolean_contract')
    so_boolean = fields.Boolean(
        "So Boolean", compute='get_so_co_boolean_contract')

    ml_partner_id = fields.Many2one('res.partner', stirng='Partner')

    # _constraints = [(_check_main_line, 'You can not have two Main Meters !!!',['main_meter']),
    #                 (_check_all_region, 'You can not have two Different Regions on one contract !!!',['region_id']),
    #                 (_check_duplicate_mpan_code, 'Duplicate Meter ID Found !!!',['mpan_code'])]

    @api.onchange('ml_partner_id')
    def partner_onchange(self):
        res = {}
        ele_line_ids = []
        gas_line_ids = []
        partner_rec = self.ml_partner_id
        for line in partner_rec.electric_info_line:
            ele_line_ids.append(line.id)
        for gas_line in partner_rec.gas_info_line:
            gas_line_ids.append(gas_line.id)
        res.update({'domain':
                    {'electric_info_line_id': [('id', 'in', ele_line_ids)],
                     'gas_info_line_id': [('id', 'in', gas_line_ids)]}})
        return res

    @api.onchange('electric_info_line_id')
    def changed_long_mpnn_id(self):
        electric_info_line_obj = self.env['electric.info.line']
        if self.electric_info_line_id:
            for electric_info_line_data in self.electric_info_line_id:
                self.mpan_code = electric_info_line_data.long_mpan
        self.mpan_code = ''

    @api.onchange('gas_info_line_id')
    def changed_mprn_id(self):
        if self.gas_info_line_id:
            for gas_info_line_data in self.gas_info_line_id:
                self.mpan_code = gas_info_line_data.mprn
        self.mpan_code = ''

    def update_meter_data_line(self):  # todo
        for self_obj in self:
            if self_obj.mpan_code:
                if self_obj.contract_id:
                    categ_id = self_obj.contract_id.categ_id.id
                    supp_id = self_obj.contract_id.supplier_id.id
                    duration = self_obj.contract_id.year_duration
                    contract_type_id = \
                        self_obj.contract_id.contract_type_id and \
                        self_obj.contract_id.contract_type_id.id or False
                    partner = self_obj.contract_id.partner_id and \
                        self_obj.contract_id.partner_id.id or False
                    usage = self_obj.contract_id.usage
                    start_date = self_obj.contract_id.start_date
                    end_date = self_obj.contract_id.end_date
                elif self_obj.sale_order_line_id:
                    categ_id = self_obj.sale_order_line_id.categ_id.id
                    supp_id = self_obj.sale_order_line_id.supplier_id.id
                    duration = self_obj.sale_order_line_id.year_duration
                    contract_type_id = \
                        self_obj.sale_order_line_id.contract_type_id and \
                        self_obj.sale_order_line_id.contract_type_id.id or \
                        False
                    partner = \
                        self_obj.sale_order_line_id.order_id.partner_id and \
                        self_obj.sale_order_line_id.order_id.partner_id.id or \
                        False
                    usage = self_obj.sale_order_line_id.usage
                    start_date = self_obj.sale_order_line_id.start_date
                    end_date = self_obj.sale_order_line_id.end_date
                else:
                    categ_id = False
                res = self.mpan_code_change()
                # self.write(cr, uid, ids, res['value'], context)
            # else:
            #     raise osv.except_osv(
            #         _('Error!'), _("Please enter a valid MPAN Code."))
        return True

    @api.model
    def copy(self, default=None):
        if default is None:
            default = {}
        if 'button_click_call' in self._context:
            default.update({
                'standing_charge': 0.0000,
                'primary_rate': 0.0000,
                'secondary_rate': 0.0000,
                'tertiary_rate': 0.0000,
                'standing_charge_sell': 0.0000,
                'primary_rate_sell': 0.0000,
                'secondary_rate_sell': 0.0000,
                'tertiary_rate_sell': 0.0000,
                'other_price_1': 0.0000,
                'other_price_2': 0.0000,
                'other_price_1_sell': 0.0000,
                'other_price_2_sell': 0.0000,
                'renew_check': True,
                'product_uom_qty': 0.00,
                'uplift_value': 0.00,
                'meter_read_date': False,
                'meter_read': 0.00,
            })

        return super(MeterDataLine, self).copy(default=default)

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('meter.data.line') or '/'
        vals['name'] = seq

        # if vals['standing_charge_sell_dummy']:
        #     vals['standing_charge_sell'] = vals['standing_charge_sell_dummy']
        # if vals['primary_rate_sell_dummy']:
        #     vals['primary_rate_sell'] = vals['standing_charge_sell_dummy']
        # if vals['secondary_rate_sell_dummy']:
        #     vals['secondary_rate_sell'] = vals['secondary_rate_sell_dummy']
        # if vals['tertiary_rate_sell_dummy']:
        #     vals['tertiary_rate_sell'] = vals['tertiary_rate_sell_dummy']
        # if vals['other_price_1_sell_dummy']:
        #     vals['other_price_1_sell'] = vals['other_price_1_sell_dummy']
        # if vals['other_price_2_sell_dummy']:
        #     vals['other_price_2_sell'] = vals['other_price_2_sell_dummy']
        # if vals['fit_rate_sell_dummy']:
        #     vals['fit_rate_sell'] = vals['fit_rate_sell_dummy']

        # if vals['standing_charge_sell'] and vals['uplift_value']:
        #     vals['standing_charge'] = self.standing_charge_sell_change()
        # print("*------>", vals['standing_charge'])
        # print("#>>>", self.standing_charge_sell_change())

        res = super(MeterDataLine, self).create(vals)
        if vals.get('contract_id'):
            contract = self.env['res.contract'].sudo().search(
                [('id', '=', vals.get('contract_id'))])
            contract.write({
                'meter_data_id': res.id,
            })
            print('--print res:::>>>>>', res)

        return res

    def write(self, vals):
        print('---vals printed::>>>>', vals)
        if vals.get("standing_charge_sell"):
            vals['standing_charge'] = vals.get(
                "standing_charge_sell") - self.uplift_value
        if vals.get('primary_rate_sell'):
            vals['primary_rate'] = vals.get(
                'primary_rate_sell') - self.uplift_value
        if vals.get('secondary_rate_sell'):
            vals['secondary_rate'] = vals.get(
                'secondary_rate_sell') - self.uplift_value
        if vals.get('tertiary_rate_sell'):
            vals['tertiary_rate'] = vals.get(
                'tertiary_rate_sell') - self.uplift_value
        if vals.get('kva_charge_sell'):
            vals['kva_charge'] = vals.get('kva_charge_sell')

        res = super(MeterDataLine, self).write(vals)
        if self.co_boolean:
            # contract_id.rec_name[:2] == 'CO'
            total_usage = 0.00
            total_usage += self.product_uom_qty
            self.contract_id.usage = total_usage
            self.contract_id.uplift_value = self.uplift_value

        if self.so_boolean:
            total_usage = 0.00
            total_usage += self.product_uom_qty
            self.contract_id.sale_usage = total_usage
            self.contract_id.sale_uplift_value = self.uplift_value

        return res

    @api.model
    def unlink(self):
        meter_data_browse = self
        if meter_data_browse.contract_id:
            total_usage = 0.00
            meter_data_ids = self.browse(
                [('contract_id', '=', meter_data_browse.contract_id)])
            for meter_data in meter_data_ids:
                total_usage += meter_data.product_uom_qty
            meter_data_browse.contract_id.write(
                {'usage': total_usage})

    # @api.onchange('contract_id')
    # def onchange_so_co_boolean(self):
    #     if self.contract_id.rec_name[:2] == 'SO':
    #         self.so_boolean = True
    #         self.co_boolean = False
    #     else:
    #         self.co_boolean = True
    #         self.so_boolean = False

    @api.depends('so_boolean', 'co_boolean', 'utility_type')
    def get_so_co_boolean_contract(self):
        for rec in self:
            if rec.contract_id:
                if rec.contract_id.rec_name[:2] == 'SO':
                    rec.so_boolean = rec.contract_id.so_boolean
                    rec.co_boolean = False
                    utility_type = ''
                    if rec.contract_id.sale_categ_id.name == 'Electricity':
                        utility_type = 'ele'
                    elif rec.contract_id.sale_categ_id.name == 'Gas':
                        utility_type = 'gas'
                    rec.utility_type = utility_type
                elif rec.contract_id.rec_name[:2] == 'CO':
                    rec.co_boolean = rec.contract_id.co_boolean
                    rec.so_boolean = False
                    rec.utility_type = rec.contract_id.utility_type
                else:
                    rec.co_boolean = False
                    rec.so_boolean = False
                    rec.utility_type = False

    #
    # def _compute_contract_button(self):
    #     for rec in self:
    #         orders = self.env['res.contract'].search([('meter_data_id', '=', rec.id)])
    #         # rec.update({"meter_data" : len(orders.ids)})
    #         rec.contract_button = len(orders)

    def action_view_contract(self):
        print('---first 2 letters of contract id :::>>>>>',
              self.contract_id.rec_name[:2])
        if self.co_boolean:
            order = self.env['res.contract'].search(
                [('meter_data_id', '=', self.id)])
            action = self.env.ref('dernetz.contract_action_view').read()[0]
            if len(order) == 1:
                action['views'] = [
                    (self.env.ref('dernetz.contract_form_view').id, 'form')]
                action['res_id'] = order.id
            elif len(order) > 1:
                action['domain'] = [('id', 'in', order.ids)]
            else:
                return {'name': 'Contract Form',
                        # 'view_type': 'form',
                        'view_mode': 'tree',
                        'views': [(self.env.ref('dernetz.contract_form_view').id, 'form')],
                        'res_model': 'res.contract',
                        'view_id': self.env.ref('dernetz.contract_form_view').id,
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'context': {'default_meter_data_id': self.id}
                        }
        elif self.so_boolean:
            order = self.env['res.contract'].search(
                [('sale_meter_data_id', '=', self.id)])
            action = self.env.ref('dernetz.sale_action_view').read()[0]
            if len(order) == 1:
                action['views'] = [
                    (self.env.ref('dernetz.sale_form_view_sysadmin').id, 'form')]
                action['res_id'] = order.id
            elif len(order) > 1:
                action['domain'] = [('id', 'in', order.ids)]
            else:
                return {'name': 'Sale Form',
                        # 'view_type': 'form',
                        'view_mode': 'tree',
                        'views': [(self.env.ref('dernetz.sale_form_view_sysadmin').id, 'form')],
                        'res_model': 'res.contract',
                        'view_id': self.env.ref('dernetz.sale_form_view_sysadmin').id,
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'context': {'default_sale_meter_data_id': self.id}
                        }
        elif self.contract_id.co_boolean and not self.contract_id.so_boolean:
            order = self.env['res.contract'].search(
                [('meter_data_id', '=', self.id)])
            action = self.env.ref('dernetz.contract_action_view').read()[0]
            if len(order) == 1:
                action['views'] = [
                    (self.env.ref('dernetz.contract_form_view').id, 'form')]
                action['res_id'] = order.id
            elif len(order) > 1:
                action['domain'] = [('id', 'in', order.ids)]
            else:
                return {'name': 'Contract Form',
                        # 'view_type': 'form',
                        'view_mode': 'tree',
                        'views': [(self.env.ref('dernetz.contract_form_view').id, 'form')],
                        'res_model': 'res.contract',
                        'view_id': self.env.ref('dernetz.contract_form_view').id,
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'context': {'default_meter_data_id': self.id}
                        }
        return action

    # @api.onchange("mpan_code")
    # def mpan_code_change(self):
    #
    #     for rec in self:
    #         if rec.mpan_code and len(rec.mpan_code) == 21:
    #             profile_id = self.env['res.profile'].search([('code', '=', rec.mpan_code[:2])])
    #             region_id = self.env['res.region'].search([('code', '=', rec.mpan_code[8:10])])
    #
    #             rec.region_id = region_id.id
    #             rec.profile_id = profile_id.id
    #             rec.mtc_code = rec.mpan_code[2:5]

    # @api.onchange("electric_info_line_id", "gas_info_line_id")
    # def change_long_mpnn_id(self):
    #
    #     for rec in self:
    #         rec.mpan_code = rec.electric_info_line_id.long_mpan
    #         rec.mpr_code = rec.gas_info_line_id.mprn

    @api.onchange("electric_info_line_id")
    def onchange_long_mpan(self):
        for rec in self:
            if rec.electric_info_line_id:
                rec.mpan_code = rec.electric_info_line_id.long_mpan.replace(
                    '-', '')
                if rec.mpan_code and len(rec.mpan_code) == 21:
                    profile_id = self.env['res.profile'].search(
                        [('code', '=', rec.mpan_code[:2])])
                    region_id = self.env['res.region'].search(
                        [('code', '=', rec.mpan_code[8:10])])

                    rec.region_id = region_id.id
                    rec.profile_id = profile_id.id
                    rec.mtc_code = rec.mpan_code[2:5]

            else:
                rec.mpan_code = ''
                rec.region_id = ''
                rec.profile_id = ''
                rec.mtc_code = ''

    @api.onchange('gas_info_line_id')
    def onchange_gas_mpr(self):
        for rec in self:
            if rec.gas_info_line_id.mprn:
                rec.mpr_code = rec.gas_info_line_id.mprn
            else:
                rec.mpr_code = ''

    def fit_rate_compute(self):
        for rec in self:
            rec.fit_rate_sell = rec.fit_rate
            rec.fit_rate_sell_dummy = rec.fit_rate

    # def fit_rate_sell_compute(self):
    #     for rec in self:
    #
    #         rec.fit_rate_sell = rec.fit_rate
    #         print("*****************",rec.fit_rate_sell)

    def other_price_2_rate_compute(self):
        for rec in self:
            if rec.other_price_2:
                rec.other_price_2_sell = rec.other_price_2 + rec.uplift_value
                rec.other_price_2_sell_dummy = rec.other_price_2 + rec.uplift_value

    def other_price_1_rate_compute(self):
        for rec in self:
            if rec.other_price_1:
                rec.other_price_1_sell = rec.other_price_1 + rec.uplift_value
                rec.other_price_1_sell_dummy = rec.other_price_1 + rec.uplift_value

    @api.onchange("tertiary_rate_sell")
    def tertiary_rate_sell_change(self):
        for rec in self:
            if rec.tertiary_rate_sell:
                rec.tertiary_rate = rec.tertiary_rate_sell - rec.uplift_value
                rec.tertiary_rate_sell_dummy = rec.tertiary_rate_sell - rec.uplift_value
            else:
                rec.tertiary_rate = 0
                rec.tertiary_rate_sell_dummy = 0

    @api.onchange("tertiary_rate")
    def tertiary_rate_change(self):
        for rec in self:
            if rec.tertiary_rate:
                rec.tertiary_rate_sell = rec.tertiary_rate + rec.uplift_value
                rec.tertiary_rate_sell_dummy = rec.tertiary_rate + rec.uplift_value

    @api.onchange("secondary_rate_sell")
    def secondary_rate_sell_change(self):
        for rec in self:
            if rec.secondary_rate_sell:
                rec.secondary_rate = rec.secondary_rate_sell - rec.uplift_value
                rec.secondary_rate_sell_dummy = rec.secondary_rate_sell - rec.uplift_value

            else:
                rec.secondary_rate = 0
                rec.secondary_rate_sell_dummy = 0

    @api.onchange("secondary_rate")
    def secondary_rate_compute(self):
        for rec in self:
            if rec.secondary_rate:
                rec.secondary_rate_sell = rec.secondary_rate + rec.uplift_value
                rec.tertiary_rate_sell_dummy = rec.secondary_rate + rec.uplift_value

    @api.onchange("primary_rate_sell")
    def primary_rate_sell_change(self):
        for rec in self:

            if rec.primary_rate_sell:
                print('--in if condition primary rate selll ::>>>',
                      rec.primary_rate_sell)
                rec.primary_rate = rec.primary_rate_sell - rec.uplift_value
                rec.primary_rate_sell_dummy = rec.primary_rate_sell - rec.uplift_value
            else:
                print('--in else condition primary rate selll ::>>>',
                      rec.primary_rate_sell)
                rec.primary_rate = 0
                rec.primary_rate_sell_dummy = 0

    @api.onchange("primary_rate")
    def primary_rate_change(self):
        for rec in self:
            if rec.primary_rate:
                rec.primary_rate_sell = rec.primary_rate + rec.uplift_value
                rec.primary_rate_sell_dummy = rec.primary_rate + rec.uplift_value

    @api.onchange("standing_charge")
    def standing_charge_change(self):
        for rec in self:
            if rec.standing_charge:
                rec.standing_charge_sell = rec.standing_charge
                rec.standing_charge_sell_dummy = rec.standing_charge

    @api.onchange("standing_charge_sell")
    def standing_charge_sell_change(self):
        for rec in self:
            print('--print standing charge ::>>>>', rec.standing_charge)
            if rec.standing_charge_sell:
                print('in if condition standing charge sell ::>>>>',
                      rec.standing_charge_sell)
                print('in if condition standing charge ::>>>>',
                      rec.standing_charge)
                rec.standing_charge = rec.standing_charge_sell
                rec.standing_charge_sell_dummy = rec.standing_charge_sell

            else:
                rec.price_unit = False
                rec.standing_charge = 0.0000
                rec.standing_charge_sell_dummy = 0.0000

            if rec.standing_charge_sell == 0.00:
                rec.price_unit = False
                rec.standing_charge = 0.0000
                rec.standing_charge_sell_dummy = 0.0000

    def quote_button(self):

        quote_button_form = self.env.ref(
            'dernetz.action_quote_button_pricetool', False)
        return {'name': 'Quote Button',
                'type': 'ir.actions.act_window',
                'res_model': 'meter.quote.pricing.wiz',
                # 'view_type': 'form',
                'view_mode': 'form',
                'target': 'new', }

        # @api.onchange("mpan_code", "categ_id", "supp_id", "duration",
        # "contract_type_id", "partner", "usage", "start_date",
    #               "end_date", )
    # def mpan_code_change(self):
    #     uplift = 0.0
    #     payment_type = False
    #     check_sc = False
    #     check_use_baserate = False
    #     zip = False
    #     if not self.supp_id and not self.contract_type_id and not self.partner:
    #         raise exceptions.except_orm(_('Invalid Data!'), _("You must select supplier/Customer."))
