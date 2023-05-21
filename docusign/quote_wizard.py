# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MeterQuotePricingWiz(models.TransientModel):
    _name = 'meter.quote.pricing.wiz'
    _description = "Meter Quote Pricing Wiz"

    day_consumption = fields.Float('Usage')
    contract_start_date = fields.Date('Contract Start Date')
    supplier_ud_ids = fields.Many2many('res.partner', string='suppliers', domain=[('supplier', '=', True)])
    # supplier_ud_ids = fields.Many2many('supplier.ud',string='Suppliers')
    utility_type = fields.Selection([('ele', 'Electricity'), ('gas', 'GAS')], string='Utility Type')
    payment_method = fields.Selection([('dir_deb_mont', 'Direct Debit (Monthly)'),
                                       ('dir_deb_quat', 'Direct Debit (Quaterly)'),
                                       ('cash_cheq', 'Cash Cheque')], string='Payment Method')
    pricing_tool_ids = fields.One2many('pricing.tool', 'pricing_tool_id', 'Pricing Tool')
    current_supplier_id = fields.Many2one('res.partner', string='Current Supplier', domain=[('supplier', '=', True)])
    uplift_value = fields.Float('Uplift Value', digits=(14, 5))
    meter_data_id = fields.Many2one('meter.data.line', 'Meter Data Line')
    mpan_code = fields.Char('MPAN / MPR')
    post_code = fields.Char('PostCode')
    smart_meter_rate = fields.Boolean('Smart')
    smart_meter_rate_selec = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('normal', 'NormalRate')],
                                              string='Smart Meter')
    co_so_both_select = fields.Boolean('CO')
    supplier_view_selec = fields.Selection([('ref', 'Supplier Reference'), ('img', 'Supplier Logo'),
                                            ('both', 'Logo & Reference'), ('none', 'Hide Supplier')],
                                           string='Display in report', default='ref')
    so_boolean = fields.Boolean('SO Boolean')
    co_boolean = fields.Boolean('CO Boolean')

    @api.model
    def default_get(self, fields):
        res = super(MeterQuotePricingWiz, self).default_get(fields)
        meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
        print ('----meter dta line :::::>>>>>',meter_data_line)
        for meter in meter_data_line:
            # for contract in meter.sale_order_line_id.order_id.partner_id:
            mpan_code = str(meter_data_line.mpan_code).replace('-', '')
            # end_date = datetime.strftime(datetime.strptime(meter.sale_order_line_id.start_date, '%Y-%m-%d').date() + \
            #            relativedelta(days=-1), '%Y-%m-%d')
            res['contract_start_date'] = meter.contract_id.start_date
            res['post_code'] = meter.contract_id.partner_id.zip
            res['day_consumption'] = meter.product_uom_qty
            res['uplift_value'] = meter.contract_id.uplift_value
            print ('--print mpan_code:::>>>>',mpan_code)
            if not mpan_code == 'False':
                res['mpan_code'] = mpan_code
            else:
                res['mpan_code'] = meter.mpr_code

            if meter.contract_id.co_boolean:
                if meter.contract_id.contract_type_id.name == 'Renewal':
                    res['current_supplier_id'] = meter.contract_id.supplier_id.id
                elif meter.contract_id.contract_type_id.name == 'Acquisition':
                    res['current_supplier_id'] = meter.contract_id.previous_supplier_id.id
            else:
                res['current_supplier_id'] = meter.contract_id.sale_supplier_id.id
                res['contract_start_date'] = meter.contract_id.sale_start_date
        return res

    @api.onchange('smart_meter_rate_selec')
    def _onchange_condition(self):
        if self.smart_meter_rate_selec == 'yes':
            self.smart_meter_rate = True
        else:
            self.smart_meter_rate = False

    @api.onchange('meter_data_id')
    def onchange_so_boolean(self):
        if self.meter_data_id.contract_id.so_boolean and not self.meter_data_id.contract_id.co_boolean:
            print ('---- print so_boolean ::>>>>', self.meter_data_id.contract_id.so_boolean)
            print ('---- print co_boolean ::>>>>', self.meter_data_id.contract_id.co_boolean)
            print ('-----in if condition for sale order::>>>>')
            self.so_boolean = True
            self.co_boolean = False
        elif self.meter_data_id.contract_id.co_boolean and self.meter_data_id.contract_id.so_boolean:
            print (' in elif condition for contract order::>>>>')
            print ('---- print co_boolean ::>>>>', self.meter_data_id.contract_id.co_boolean)
            self.co_boolean = True
            self.so_boolean = False
        else:
            self.so_boolean = True
            self.co_boolean = False

    
    def selected_prices_with_suppliers(self, pricing_tool_ids):
        supplier_list = []
        compared_list = []
        for price in pricing_tool_ids:
            if price.compare_price:
                compared_list.append(price)
                if price.supplier:
                    supplier_list.append(price.supplier)
                    #         print ("supplier_list>>>>>>>>>", supplier_list)
        suppliers = self.env.get('res.partner').search_read(
            [('ud_supplier_name', 'in', supplier_list)], ['id', 'ud_supplier_name', 'image'])
        #         print ("suppliers>>>>>>>>>", suppliers)
        for price in compared_list:
            for supplier in suppliers:
                if price.supplier == supplier.get('ud_supplier_name'):
                    price.supplier_ref = 'URL' + str(supplier.get('id'))
                    price.supplier_img = supplier.get('image')
        return compared_list

    
    def open_mail_wiz(self):
        for rec in self:
            supplier_view_selec = rec.supplier_view_selec
            compared_price_list = []
            for price in self.selected_prices_with_suppliers(rec.pricing_tool_ids):
                if price.compare_price == True:
                    compared_price_list.append([
                        price.duration_term,
                        price.plan_type,
                        price.uplift_value,
                        price.standing_charge,
                        price.primary_rate,
                        price.secondary_rate,
                        price.tertiary_rate,
                        price.fit_rate,
                        price.annual_price_inclusive,
                        price.extra_info,
                        price.supplier,
                        price.supplier_ref,
                        price.supplier_img
                    ])
                    #         assert len(self.ids) == 1
            ir_model_data = self.env.get('ir.model.data')
            try:
                template_id = \
                    ir_model_data.get_object_reference('dernetz', 'price_comparision_email_template')[1]
            # print ("---temp::>>",template_id)
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            # print ("---comp",compose_form_id)
            except ValueError:
                compose_form_id = False

            ctx = dict()
            ctx.update({
                'lines': compared_price_list,
                'supplier_view_selec': supplier_view_selec,
                'default_model': 'meter.quote.pricing.wiz',
                'default_res_id': rec.id,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                # 'mark_so_as_sent': True,
                'force_email': True
            })
        # print "------::>>>>>>context", context
        #         print "------::>>>>>>ctx::>>>>>>>", ctx
        return {
            'type': 'ir.actions.act_window',
            # # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    # 
    # def get_rates(self):
    #     return True

    
    def api_get_suppliers(self):

        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuser in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_elec_plan_dur_dict = []
            supp_gas_plan_dur_dict = []
            suppliers = False
            if self.utility_type == 'ele':
                suppliers = self.env['res.partner'].sudo().search(
                    [('supplier', '=', True), ('supplier_typ_elec', '=', True)])
            if self.utility_type == 'gas':
                suppliers = self.env['res.partner'].sudo().search(
                    [('supplier', '=', True), ('supplier_typ_gas', '=', True)])
            for one_supplier in suppliers:
                supplier_data.append({
                    'Supplier': one_supplier.name
                })
                plans_elec = []
                plans_gas = []
                for one_plan in one_supplier.electric_plans_info_line:
                    one_plan_dict = {}
                    if one_plan.duration:
                        one_plan_dict['Duration'] = one_plan.duration
                    if one_plan.plan_type:
                        one_plan_dict['PlanType'] = one_plan.plan_type
                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                        one_plan_dict['Uplift'] = one_plan.uplift_val
                    if one_plan_dict:
                        plans_elec.append(one_plan_dict)

                for one_plan in one_supplier.gass_plans_info_line:
                    one_plan_dict = {}
                    if one_plan.duration:
                        one_plan_dict['Duration'] = one_plan.duration
                    if one_plan.plan_type:
                        one_plan_dict['PlanType'] = one_plan.plan_type
                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                        one_plan_dict['Uplift'] = one_plan.uplift_val
                    if one_plan_dict:
                        plans_gas.append(one_plan_dict)

                if plans_elec:
                    supp_elec_plan_dur_dict.append({
                        'Supplier': one_supplier.supplier_name_elec,
                        'Plans': plans_elec,
                    })
                if plans_gas:
                    supp_gas_plan_dur_dict.append({
                        'Supplier': one_supplier.supplier_name_gas,
                        'Plans': plans_gas,
                    })

            # meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
            date = self.contract_start_date
            for meter in self.meter_data_id:
                for contract in meter.contract_id:
                    print ("--partnername::>>>>", contract.partner_id.name)
                    if self.utility_type == 'ele':
                        print ("----not renewal either acquisition electric rates;;;>>>>")
                        mpan_code = str(self.mpan_code).replace('-', '')
                        electric_supply = {
                            "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                            "MPANTop": mpan_code[0:8],
                            "MPANBottom": mpan_code[8:21],
                            "SmartMeter": self.smart_meter_rate,
                            "ContractEndDate": str(date),
                            "NoOfPrompts": 1,
                            "NightConsumption": {"Amount": 0, "Type": 'Night'},
                            "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                        }
                        payment_method = ''
                        if self.payment_method == 'dir_deb_mont':
                            payment_method = 'Direct Debit (Monthly)'
                        if self.payment_method == 'dir_deb_quat':
                            payment_method = 'Direct Debit (Quaterly)'
                        if self.payment_method == 'cash_cheq':
                            payment_method = 'Cash Cheque'

                        values = {
                            "quoteDetails": {
                                "Contact": {
                                    "ContactName": contract.partner_id.name,
                                    "Telephone": {
                                        "Number": contract.partner_id.phone},
                                    "EmailAddress": contract.partner_id.email},
                                "SecurityDetails": security_details,
                                "ElectricSupply": electric_supply,
                                "Uplift": self.uplift_value,
                                # "Renewal": self.is_contract_renewal,
                                # "CurrentSupplier": 'British Gas',
                                "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                "COT": False,
                                "PaymentMethod": payment_method,
                                "QuoteDefinitions": supp_elec_plan_dur_dict,

                            },

                            "Settings": [
                                {"key": "BG_WithoutSC", "value": False},
                                {"key": "Corona_FixedRates", "value": False},
                                {"key": "Corona_AllInclusiveRates", "value": False},
                                {"key": "Dong_SCType", "value": "normal"},
                                {"key": "CreditScore", "value": 50},
                                {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                {"key": "EDFSME_OnePlusYear", "value": True},
                                {"key": "EON_ExcludeDiscounts", "value": False},
                                {"key": "Gazprom_LowSC", "value": False},
                                {"key": "Gazprom_WithSC", "value": False},
                                {"key": "Haven_ProductType", "value": "complete"},
                                {"key": "Haven_Amr_Rates", "value": False},
                                {"key": "Opus_BaseRates", "value": False},
                                {"key": "Opus_GasWithSC", "value": True},
                                {"key": "OVO_GreenRates", "value": False},
                                {"key": "SSE_AmrRates", "value": False},
                                {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                {"key": "TGP_ReducedYearMonths", "value": 0},
                                {"key": "TGP_GasWithSC", "value": False},
                                {"key": "TGP_ElecBasketRates", "value": False},
                                {"key": "TGP_GasBasketRates", "value": False},
                                {"key": "UGP_LowCreditRates", "value": False},
                                {"key": "UGP_PubRates", "value": False},
                                {"key": "YGP_CommsType", "value": "Monthly"},
                                {"key": "YGP_SCharge", "value": False}
                            ]
                        }

                        # print '------current supplier elec--:::>>>>', contract.supplier_for_docusign
                        # print '------values----',values
                        http = urllib3.PoolManager()
                        encoded_data = json.dumps(values).encode('utf-8')
                        data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                   body=encoded_data, headers={'Content-Type': 'application/json'})
                        # print ("----print request ::>>>>>", data_encode)
                        response = json.loads(data_encode.data.decode('utf-8'))
                        # print ("----dataencodeprinted::>>>>>>>", data_encode)
                        # print ("==============",response)
                        # print "---response --------rr---", response

                        # print dict(response)
                        self.write({'pricing_tool_ids': [(5, 0)]})
                        if response and response.get("GetElectricRatesResult") and \
                                        response["GetElectricRatesResult"]["Rates"] != []:
                            for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                elec_gas_pricing_tool_val = {
                                    'pricing_tool_id': self.id
                                }
                                if elec_supp_detail.get("Supplier"):
                                    elec_gas_pricing_tool_val.update({
                                        'supplier': elec_supp_detail.get("Supplier")
                                    })
                                if elec_supp_detail.get("Uplift"):
                                    elec_gas_pricing_tool_val.update({
                                        'uplift_value': elec_supp_detail.get("Uplift")
                                    })
                                if elec_supp_detail.get("StandingCharge"):
                                    elec_gas_pricing_tool_val.update({
                                        'standing_charge': elec_supp_detail.get("StandingCharge")
                                    })
                                if elec_supp_detail.get("DayUnitrate"):
                                    elec_gas_pricing_tool_val.update({
                                        'primary_rate': elec_supp_detail.get("DayUnitrate")
                                    })
                                if elec_supp_detail.get("NightUnitrate"):
                                    elec_gas_pricing_tool_val.update({
                                        'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                    })
                                if elec_supp_detail.get("WendUnitrate"):
                                    elec_gas_pricing_tool_val.update({
                                        'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                    })
                                if elec_supp_detail.get("Term"):
                                    elec_gas_pricing_tool_val.update({
                                        'duration_term': elec_supp_detail.get("Term")
                                    })
                                if elec_supp_detail.get("PlanType"):
                                    elec_gas_pricing_tool_val.update({
                                        'plan_type': elec_supp_detail.get("PlanType")
                                    })
                                if elec_supp_detail.get("AnnualPriceInclusive"):
                                    elec_gas_pricing_tool_val.update({
                                        'annual_price_inclusive': elec_supp_detail.get(
                                            "AnnualPriceInclusive")
                                    })
                                if elec_supp_detail.get("Ref"):
                                    elec_gas_pricing_tool_val.update({
                                        'validation_ref': elec_supp_detail.get("Ref")
                                    })
                                if self.smart_meter_rate_selec == 'yes':
                                    if elec_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'extra_info': elec_supp_detail.get("SC")
                                        })
                                        # [41:46]
                                    if elec_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'fit_rate': elec_supp_detail.get("Fits")
                                        })
                                        # [75:83]
                                elif self.smart_meter_rate_selec == 'no':
                                    if elec_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'extra_info': elec_supp_detail.get("SC")
                                        })
                                    if elec_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'fit_rate': elec_supp_detail.get("Fits")
                                        })
                                # if self.smart_meter_rate_selec == 'no':
                                #     if elec_supp_detail.get("ExtraInfo"):
                                #         elec_gas_pricing_tool_val.update({
                                #             'extra_info': elec_supp_detail.get("ExtraInfo")[41:46]
                                #         })
                                #         print "---extrainfo::::SC",elec_supp_detail.get("ExtraInfo")[41:46]
                                #     if elec_supp_detail.get("ExtraInfo"):
                                #         elec_gas_pricing_tool_val.update({
                                #             'fit_rate': elec_supp_detail.get("ExtraInfo")[75:83]
                                #         })
                                #     print "----extrainfo----Fitrates----->>>",
                                # elec_supp_detail.get("ExtraInfo")[75:83]

                                # print "=============================="
                                # print "---one_pricing_tool_val--", elec_gas_pricing_tool_val

                                pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                # print "----pricing_tool--", pricing_tool
                                # supplier_ref_method = self.supplier_ref_get_value()
                        else:
                            raise ValidationError(
                                'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                '\n ######################\n %s' % json.dumps(
                                    response.get("GetElectricRatesResult"),
                                    indent=3))

                        return {
                            'name': 'Quote',
                            'type': 'ir.actions.act_window',
                            # # 'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'meter.quote.pricing.wiz',
                            'res_id': self.id,
                            'target': 'new',
                        }

                    elif self.utility_type == 'gas':
                        print ("----not renewal nor eacquisition gas rates;;;>>>>")
                        mpan_code = str(self.mpan_code).replace('-', '')
                        gas_supply = {
                            "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                            "MPR": mpan_code,
                            "SmartMeter": self.smart_meter_rate,
                            "ContractRenewalDate": str(date),

                        }
                        payment_method = ''
                        if self.payment_method == 'dir_deb_mont':
                            payment_method = 'Direct Debit (Monthly)'
                        if self.payment_method == 'dir_deb_quat':
                            payment_method = 'Direct Debit (Quaterly)'
                        if self.payment_method == 'cash_cheq':
                            payment_method = 'Cash Cheque'

                        # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                        values = {
                            "quoteDetails": {
                                "Contact": {
                                    "ContactName": contract.partner_id.name,
                                    "Telephone": {
                                        "Number": contract.partner_id.phone},
                                    "EmailAddress": contract.order_id.partner_id.email},
                                "SecurityDetails": security_details,
                                "GasSupply": gas_supply,
                                "PostCode": self.post_code,
                                "Uplift": self.uplift_value,
                                # "Renewal": self.is_contract_renewal,
                                # "CurrentSupplier": 'British Gas',
                                "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                "COT": False,
                                "PaymentMethod": payment_method,
                                "QuoteDefinitions": supp_gas_plan_dur_dict
                            },
                            "Settings": [
                                {"key": "BG_WithoutSC", "value": False},
                                {"key": "Corona_FixedRates", "value": False},
                                {"key": "Corona_AllInclusiveRates", "value": False},
                                {"key": "Dong_SCType", "value": "normal"},
                                {"key": "CreditScore", "value": 50},
                                {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                {"key": "EDFSME_OnePlusYear", "value": True},
                                {"key": "EON_ExcludeDiscounts", "value": True},
                                {"key": "Gazprom_LowSC", "value": False},
                                {"key": "Gazprom_WithSC", "value": False},
                                {"key": "Haven_ProductType", "value": "standard"},
                                {"key": "Haven_Amr_Rates", "value": False},
                                {"key": "Opus_BaseRates", "value": False},
                                {"key": "Opus_GasWithSC", "value": False},
                                {"key": "OVO_GreenRates", "value": False},
                                {"key": "SSE_AmrRates", "value": False},
                                {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                {"key": "TGP_ReducedYearMonths", "value": 0},
                                {"key": "TGP_GasWithSC", "value": True},
                                {"key": "TGP_ElecBasketRates", "value": False},
                                {"key": "TGP_GasBasketRates", "value": False},
                                {"key": "UGP_LowCreditRates", "value": False},
                                {"key": "UGP_PubRates", "value": False},
                                {"key": "YGP_CommsType", "value": "Monthly"},
                                {"key": "YGP_SCharge", "value": False}
                            ]
                        }

                        # print '---current supply gas-----:::>>>>',meter.sale_ord
                        # er_line_id.supplier_id.ud_supplier_name
                        http = urllib3.PoolManager()
                        encoded_data = json.dumps(values).encode('utf-8')
                        data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                   body=encoded_data, headers={'Content-Type': 'application/json'})
                        # print ("----print request ::>>>>>", data_encode)
                        response = json.loads(data_encode.data.decode('utf-8'))
                        # print ("----dataencodeprinted::>>>>>>>", data_encode)

                        # print "---response --------rr---", type(response)
                        # print ("---response --------rr---",response)
                        self.write({'pricing_tool_ids': [(5, 0)]})
                        response = dict(response)
                        if response and response.get("GetGasRatesResult") and \
                                        response["GetGasRatesResult"]["Rates"] != []:
                            for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                elec_gas_pricing_tool_val = {
                                    'pricing_tool_id': self.id
                                }
                                if gas_supp_detail.get("Supplier"):
                                    elec_gas_pricing_tool_val.update({
                                        'supplier': gas_supp_detail.get("Supplier")
                                    })
                                if gas_supp_detail.get("Uplift"):
                                    elec_gas_pricing_tool_val.update({
                                        'uplift_value': gas_supp_detail.get("Uplift")
                                    })
                                if gas_supp_detail.get("StandingCharge"):
                                    elec_gas_pricing_tool_val.update({
                                        'standing_charge': gas_supp_detail.get("StandingCharge")
                                    })
                                if gas_supp_detail.get("DayUnitrate"):
                                    elec_gas_pricing_tool_val.update({
                                        'primary_rate': gas_supp_detail.get("DayUnitrate")
                                    })
                                if gas_supp_detail.get("NightUnitrate"):
                                    elec_gas_pricing_tool_val.update({
                                        'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                    })
                                if gas_supp_detail.get("WendUnitrate"):
                                    elec_gas_pricing_tool_val.update({
                                        'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                    })
                                if gas_supp_detail.get("Term"):
                                    elec_gas_pricing_tool_val.update({
                                        'duration_term': gas_supp_detail.get("Term")
                                    })
                                if gas_supp_detail.get("PlanType"):
                                    elec_gas_pricing_tool_val.update({
                                        'plan_type': gas_supp_detail.get("PlanType")
                                    })
                                if gas_supp_detail.get("AnnualPriceInclusive"):
                                    elec_gas_pricing_tool_val.update({
                                        'annual_price_inclusive': gas_supp_detail.get(
                                            "AnnualPriceInclusive")
                                    })
                                if gas_supp_detail.get("Ref"):
                                    elec_gas_pricing_tool_val.update({
                                        'validation_ref': gas_supp_detail.get("Ref")
                                    })
                                if self.smart_meter_rate_selec == 'yes':
                                    if gas_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'extra_info': gas_supp_detail.get("SC")
                                        })
                                        # [41:46]
                                    if gas_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'fit_rate': gas_supp_detail.get("Fits")
                                        })
                                        # [75:83]
                                elif self.smart_meter_rate_selec == 'no':
                                    if gas_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'extra_info': gas_supp_detail.get("SC")
                                        })
                                    if gas_supp_detail.get("ExtraInfo"):
                                        elec_gas_pricing_tool_val.update({
                                            'fit_rate': gas_supp_detail.get("Fits")
                                        })
                                # if self.smart_meter_rate == True:
                                #     if gas_supp_detail.get("ExtraInfo"):
                                #         elec_gas_pricing_tool_val.update({
                                #             'extra_info': gas_supp_detail.get("ExtraInfo")[41:46]
                                #         })
                                #     if gas_supp_detail.get("ExtraInfo"):
                                #         elec_gas_pricing_tool_val.update({
                                #             'fit_rate': gas_supp_detail.get("ExtraInfo")[75:83]
                                #         })

                                # print "---one_pricing_tool_val--",elec_gas_pricing_tool_val

                                pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                # print "----pricing_tool--",pricing_tool
                                # supplier_ref_method = self.supplier_ref_get_value()
                        else:
                            raise ValidationError(
                                'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                '\n ######################\n %s' % json.dumps(
                                    response.get("GetGasRatesResult"), indent=3))

                        return {
                            'name': 'Quote',
                            'type': 'ir.actions.act_window',
                            # # 'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'meter.quote.pricing.wiz',
                            'res_id': self.id,
                            'target': 'new',
                        }

    
    def api_selected_suppliers(self):
        # print "---------context active_id", self._context
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_elec_plan_dur_dict = []
            supp_gas_plan_dur_dict = []
            suppliers = False
            # if self.supplier_ud_ids:
            #     for ud_core_sup in self.supplier_ud_ids:
            #         supp_name_partner = ud_core_sup.name
            if self.supplier_ud_ids:
                for ud_core_sup in self.supplier_ud_ids:
                    supp_name_partner = ud_core_sup.name
                    if self.utility_type == 'ele':
                        suppliers = self.env['res.partner'].sudo().search(
                            [('supplier_name_elec', '=', supp_name_partner), ('supplier_typ_elec', '=', True)])
                    if self.utility_type == 'gas':
                        suppliers = self.env['res.partner'].sudo().search(
                            [('supplier_name_gas', '=', supp_name_partner), ('supplier_typ_gas', '=', True)])
            # if self.utility_type == 'ele':
            #     suppliers = self.env['res.partner'].sudo().search(
            #         [('supplier', '=', True), ('supplier_typ_elec', '=', True)])
            # if self.utility_type == 'gas':
            #     suppliers = self.env['res.partner'].sudo().search(
            #         [('supplier', '=', True), ('supplier_typ_gas', '=', True)])
                    for one_supplier in suppliers:
                        supplier_data.append({
                            'Supplier': one_supplier.name
                        })
                        plans_elec = []
                        plans_gas = []
                        for one_plan in one_supplier.electric_plans_info_line:
                            one_plan_dict = {}
                            if one_plan.duration:
                                one_plan_dict['Duration'] = one_plan.duration
                            if one_plan.plan_type:
                                one_plan_dict['PlanType'] = one_plan.plan_type
                            if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                one_plan_dict['Uplift'] = one_plan.uplift_val
                            if one_plan_dict:
                                plans_elec.append(one_plan_dict)

                        for one_plan in one_supplier.gass_plans_info_line:
                            one_plan_dict = {}
                            if one_plan.duration:
                                one_plan_dict['Duration'] = one_plan.duration
                            if one_plan.plan_type:
                                one_plan_dict['PlanType'] = one_plan.plan_type
                            if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                one_plan_dict['Uplift'] = one_plan.uplift_val
                            if one_plan_dict:
                                plans_gas.append(one_plan_dict)

                        if plans_elec:
                            supp_elec_plan_dur_dict.append({
                                'Supplier': supp_name_partner,
                                'Plans': plans_elec,
                            })
                            # print '-------elecplan----------', supp_elec_plan_dur_dict
                            # print '************plantypes**********', plans_elec
                        if plans_gas:
                            supp_gas_plan_dur_dict.append({
                                'Supplier': supp_name_partner,
                                'Plans': plans_gas,
                            })

                    payment_method = ''
                    if self.payment_method == 'dir_deb_mont':
                        payment_method = 'Direct Debit (Monthly)'
                    elif self.payment_method == 'dir_deb_quat':
                        payment_method = 'Direct Debit (Quaterly)'
                    else:
                        payment_method = 'Cash Cheque'

                    for meter in self.meter_data_id:
                        for contract in meter.contract_id:
                            if self.utility_type == 'ele':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }

                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": self.current_supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"]["Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': elec_supp_detail.get("DayUnitrate")
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get("AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [61:68]

                                        # print "---one_pricing_tool_val--", elec_gas_pricing_tool_val

                                        pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                        # print "----pricing_tool--", pricing_tool
                                        # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' %
                                        json.dumps(response.get("GetElectricRatesResult"), indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": self.current_supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                # print ('-------printing values::>>>>>>', values)
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = \
                                    http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                 body=encoded_data, headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetGasRatesResult") and \
                                                response["GetGasRatesResult"]["Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': gas_supp_detail.get("DayUnitrate")
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get("AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [61:68]
                                        # print "---one_pricing_tool_val--",elec_gas_pricing_tool_val

                                        pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                        # print "----pricing_tool--",pricing_tool
                                        # supplier_ref_method = self.supplier_ref_get_value()

                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(response.get("GetGasRatesResult"),
                                                                                      indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
                    else:
                        raise ValidationError("You Must Enter Suppliers in Field 'Suppliers' ")

    
    def contract_api_selected_suppliers(self):
        # print "---------context active_id", self._context
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_elec_plan_dur_dict = []
            supp_gas_plan_dur_dict = []
            suppliers = False
            if self.supplier_ud_ids:
                for ud_core_sup in self.supplier_ud_ids:
                    supp_name_partner = ud_core_sup.ud_supplier_name
                    print ("---supp name partner::>>>>", supp_name_partner)
                    if self.utility_type == 'ele':
                        suppliers = self.env['res.partner'].sudo().search(
                            [('supplier_name_elec', '=', supp_name_partner), ('supplier_typ_elec', '=', True)])
                    if self.utility_type == 'gas':
                        suppliers = self.env['res.partner'].sudo().search(
                            [('supplier_name_gas', '=', supp_name_partner), ('supplier_typ_gas', '=', True)])
                    for one_supplier in suppliers:
                        supplier_data.append({
                            'Supplier': ud_core_sup
                        })
                        plans_elec = []
                        plans_gas = []
                        for one_plan in one_supplier.electric_plans_info_line:
                            one_plan_dict = {}
                            if one_plan.duration:
                                one_plan_dict['Duration'] = one_plan.duration
                            if one_plan.plan_type:
                                one_plan_dict['PlanType'] = one_plan.plan_type
                            if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                one_plan_dict['Uplift'] = one_plan.uplift_val
                            if one_plan_dict:
                                plans_elec.append(one_plan_dict)

                        for one_plan in one_supplier.gass_plans_info_line:
                            one_plan_dict = {}
                            if one_plan.duration:
                                one_plan_dict['Duration'] = one_plan.duration
                            if one_plan.plan_type:
                                one_plan_dict['PlanType'] = one_plan.plan_type
                            if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                one_plan_dict['Uplift'] = one_plan.uplift_val
                            if one_plan_dict:
                                plans_gas.append(one_plan_dict)

                        if plans_elec:
                            supp_elec_plan_dur_dict.append({
                                'Supplier': supp_name_partner,
                                'Plans': plans_elec,
                            })
                            # print '-------elecplan----------', supp_elec_plan_dur_dict
                            # print '************plantypes**********', plans_elec
                        if plans_gas:
                            supp_gas_plan_dur_dict.append({
                                'Supplier': supp_name_partner,
                                'Plans': plans_gas,
                            })

                meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
                for meter in self.meter_data_id:
                    for contract in meter.contract_id:
                        current_date = datetime.strftime(datetime.now(), '%Y-%m-%d')
                        print ('-----printed new _date suvbtracted:::>>>>', current_date)
                        date_subtracted = (fields.Date.from_string(contract.start_date) - fields.Date.from_string(
                            current_date)).days
                        print ('----subtracted date printed ::>>>>', date_subtracted)
                        if contract.contract_type_id.name == 'Renewal':
                            # print "--contract selected rates Account type -R-::>>",contract.contract_account_id.name
                            # print "--partnername::>>>>", contract.partner_id.name
                            if self.utility_type == 'ele':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                # print '------current supplu elec----', contract.supplier_for_docusign
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"][
                                                    "Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get("AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [61:68]

                                        # print "---one_pricing_tool_val--", elec_gas_pricing_tool_val

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted >= 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--", pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                            # print "---supplier ref:>>>>",supplier_ref_method
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetElectricRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                # print ("----dataencodeprinted::>>>>>>>", data_encode)
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                response = dict(response)
                                if response and response.get("GetGasRatesResult") and \
                                                response["GetGasRatesResult"]["Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get("AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [61:68]
                                        # print "---one_pricing_tool_val--",elec_gas_pricing_tool_val

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--",pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()

                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(response.get("GetGasRatesResult"),
                                                                                      indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
                        elif contract.contract_type_id.name == 'Acquisition':
                            # print "contract Account id  -A-::>>>",contract.contract_account_id.name
                            # print "--partnername::>>>>", contract.partner_id.name
                            if self.utility_type == 'ele':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": contract.previous_supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"][
                                                    "Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get("AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [61:68]

                                        # print "---one_pricing_tool_val--", elec_gas_pricing_tool_val

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--", pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetElectricRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": contract.previous_supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                # print ("----dataencodeprinted::>>>>>>>", data_encode)
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                response = dict(response)
                                if response and response.get("GetGasRatesResult") and \
                                                response["GetGasRatesResult"]["Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get("AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [61:68]
                                        # print "---one_pricing_tool_val--",elec_gas_pricing_tool_val

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--",pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()

                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(response.get("GetGasRatesResult"),
                                                                                      indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
                        else:
                            print ("---contract selected supplier in else condition")
                            if self.utility_type == 'ele':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"]["Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [61:68]

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--", pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetElectricRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                # print ("----print request ::>>>>>", data_encode)
                                response = json.loads(data_encode.data.decode('utf-8'))
                                # print ("----dataencodeprinted::>>>>>>>", data_encode)
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})

                                if response and response.get("GetGasRatesResult") and response["GetGasRatesResult"][
                                    "Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:47]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [61:68]
                                        # print "---one_pricing_tool_val--",elec_gas_pricing_tool_val

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--",pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()

                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetGasRatesResult"), indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
            else:
                raise ValidationError("You Must Enter Suppliers in Field 'Suppliers' ")

    
    def contract_renewal_elec_current_supp_prices(self):
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_elec_plan_dur_dict = []
            meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
            for meter in self.meter_data_id:
                for contract in meter.contract_id:
                    if contract.contract_type_id.name == 'Renewal':
                        for ud_core_sup in contract.supplier_id:
                            supp_name_partner = ud_core_sup.ud_supplier_name
                            # print "---suppl name to get ", supp_name_partner

                            suppliers = self.env['res.partner'].sudo().search(
                                [('supplier_name_elec', '=', supp_name_partner), ('supplier_typ_elec', '=', True)])

                            for one_supplier in suppliers:
                                supplier_data.append({
                                    'Supplier': ud_core_sup
                                })
                                plans_elec = []
                                for one_plan in one_supplier.electric_plans_info_line:
                                    one_plan_dict = {}
                                    if one_plan.duration:
                                        one_plan_dict['Duration'] = one_plan.duration
                                    if one_plan.plan_type:
                                        one_plan_dict['PlanType'] = one_plan.plan_type
                                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                        one_plan_dict['Uplift'] = one_plan.uplift_val
                                    if one_plan_dict:
                                        plans_elec.append(one_plan_dict)

                                if plans_elec:
                                    supp_elec_plan_dur_dict.append({
                                        'Supplier': supp_name_partner,
                                        'Plans': plans_elec,
                                    })

                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {"Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": True,
                                        "CurrentSupplier": ud_core_sup.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"][
                                                    "Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })

                                        pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                        # print "----pricing_tool--", pricing_tool
                                # else:
                                #     raise ValidationError(
                                #         'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                #         '\n ######################\n %s' % json.dumps(
                                #             response.get("GetElectricRatesResult"),
                                #             indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

    
    def contract_renewal_gas_current_supp_prices(self):
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_gas_plan_dur_dict = []
            meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
            for meter in self.meter_data_id:
                for contract in meter.contract_id:
                    if contract.contract_type_id.name == 'Renewal':
                        for ud_core_sup in contract.supplier_id:
                            supp_name_partner = ud_core_sup.ud_supplier_name
                            # print "---suppl name to get ", supp_name_partner
                            suppliers = self.env['res.partner'].sudo().search(
                                [('supplier_name_gas', '=', supp_name_partner), ('supplier_typ_gas', '=', True)])

                            for one_supplier in suppliers:
                                supplier_data.append({
                                    'Supplier': ud_core_sup
                                })
                                plans_gas = []
                                for one_plan in one_supplier.gass_plans_info_line:
                                    one_plan_dict = {}
                                    if one_plan.duration:
                                        one_plan_dict['Duration'] = one_plan.duration
                                    if one_plan.plan_type:
                                        one_plan_dict['PlanType'] = one_plan.plan_type
                                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                        one_plan_dict['Uplift'] = one_plan.uplift_val
                                    if one_plan_dict:
                                        plans_gas.append(one_plan_dict)
                                if plans_gas:
                                    supp_gas_plan_dur_dict.append({
                                        'Supplier': supp_name_partner,
                                        'Plans': plans_gas,
                                    })
                                # for contract in meter.sale_order_line_id.order_id.partner_id.contract_line:

                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": True,
                                        "CurrentSupplier": ud_core_sup.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                response = dict(response)
                                if response and response.get("GetGasRatesResult") and \
                                                response["GetGasRatesResult"]["Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })

                                        pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                        # print "----pricing_tool--", pricing_tool

                                # else:
                                #     raise ValidationError(
                                #         'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                #         '\n ######################\n %s' % json.dumps(
                                #             response.get("GetGasRatesResult"),
                                #             indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

    
    def contract_renewal_elec_previous_supp_prices(self):
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_elec_plan_dur_dict = []
            meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
            for meter in self.meter_data_id:
                for contract in meter.contract_id:
                    if contract.contract_type_id.name == 'Acquisition':
                        for ud_core_sup in contract.previous_supplier_id:
                            supp_name_partner = ud_core_sup.ud_supplier_name
                            print ("---remove else statemng ", supp_name_partner)
                            # print "---previous suplier::>>>", contract.previous_supplier_id.ud_supplier_name

                            suppliers = self.env['res.partner'].sudo().search(
                                [('supplier_name_elec', '=', supp_name_partner), ('supplier_typ_elec', '=', True)])

                            for one_supplier in suppliers:
                                supplier_data.append({
                                    'Supplier': ud_core_sup
                                })
                                plans_elec = []
                                for one_plan in one_supplier.electric_plans_info_line:
                                    one_plan_dict = {}
                                    if one_plan.duration:
                                        one_plan_dict['Duration'] = one_plan.duration
                                    if one_plan.plan_type:
                                        one_plan_dict['PlanType'] = one_plan.plan_type
                                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                        one_plan_dict['Uplift'] = one_plan.uplift_val
                                    if one_plan_dict:
                                        plans_elec.append(one_plan_dict)

                                if plans_elec:
                                    supp_elec_plan_dur_dict.append({
                                        'Supplier': supp_name_partner,
                                        'Plans': plans_elec,
                                    })
                                # for contract in meter.sale_order_line_id.order_id.partner_id.contract_line:

                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {"Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": True,
                                        "CurrentSupplier": ud_core_sup.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"][
                                                    "Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })

                                        pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                        # print "----pricing_tool--", pricing_tool
                                # else:
                                #     raise ValidationError(
                                #         'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                #         '\n ######################\n %s' % json.dumps(
                                #             response.get("GetElectricRatesResult"),
                                #             indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

    
    def contract_renewal_gas_previous_supp_prices(self):
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_gas_plan_dur_dict = []
            meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
            for meter in self.meter_data_id:
                for contract in meter.contract_id:
                    if contract.contract_type_id.name == 'Acquisition':
                        for ud_core_sup in contract.previous_supplier_id:
                            supp_name_partner = ud_core_sup.ud_supplier_name
                            # print "---suppl name to get ", supp_name_partner
                            # print "---previous suplier::>>>", contract.previous_supplier_id.ud_supplier_name

                            suppliers = self.env['res.partner'].sudo().search(
                                [('supplier_name_gas', '=', supp_name_partner), ('supplier_typ_gas', '=', True)])

                            for one_supplier in suppliers:
                                supplier_data.append({
                                    'Supplier': ud_core_sup
                                })
                                plans_gas = []
                                for one_plan in one_supplier.gass_plans_info_line:
                                    one_plan_dict = {}
                                    if one_plan.duration:
                                        one_plan_dict['Duration'] = one_plan.duration
                                    if one_plan.plan_type:
                                        one_plan_dict['PlanType'] = one_plan.plan_type
                                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                                        one_plan_dict['Uplift'] = one_plan.uplift_val
                                    if one_plan_dict:
                                        plans_gas.append(one_plan_dict)
                                if plans_gas:
                                    supp_gas_plan_dur_dict.append({
                                        'Supplier': supp_name_partner,
                                        'Plans': plans_gas,
                                    })
                                    # print '************plantypes**********', plans_gas

                                # print '--contractrenewal-----', self.is_contract_renewal

                                # for contract in meter.sale_order_line_id.order_id.partner_id.contract_line:

                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                payment_method = ''
                                if self.payment_method == 'dir_deb_mont':
                                    payment_method = 'Direct Debit (Monthly)'
                                elif self.payment_method == 'dir_deb_quat':
                                    payment_method = 'Direct Debit (Quaterly)'
                                else:
                                    payment_method = 'Cash Cheque'

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": True,
                                        "CurrentSupplier": ud_core_sup.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)

                                self.write({'pricing_tool_ids': [(5, 0)]})
                                response = dict(response)
                                if response and response.get("GetGasRatesResult") and response["GetGasRatesResult"][
                                    "Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })

                                        pricing_tool = self.env['pricing.tool'].create(elec_gas_pricing_tool_val)
                                        # print "----pricing_tool--", pricing_tool
                                # else:
                                #     raise ValidationError(
                                #         'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                #         '\n ######################\n %s' % json.dumps(
                                #             response.get("GetGasRatesResult"),
                                #             indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

    
    def contract_renewal_acqui_supplier_elec_gas_rates(self):
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            supplier_data = []
            supp_elec_plan_dur_dict = []
            supp_gas_plan_dur_dict = []
            suppliers = False
            if self.utility_type == 'ele':
                # suppliers = self.env['res.partner'].sudo().search(
                #     [('supplier', '=', True), ('utili_typ', 'in', ['gas_elec_both', 'is_electric_supplier'])])
                suppliers = self.env['res.partner'].sudo().search(
                    [('supplier', '=', True), ('supplier_typ_elec', '=', True)])
            else:
                suppliers = self.env['res.partner'].sudo().search(
                    [('supplier', '=', True), ('supplier_typ_gas', '=', True)])

            payment_method = ''
            if self.payment_method == 'dir_deb_mont':
                payment_method = 'Direct Debit (Monthly)'
            elif self.payment_method == 'dir_deb_quat':
                payment_method = 'Direct Debit (Quaterly)'
            else:
                payment_method = 'Cash Cheque'

            print ('--print payment method :::>>>', payment_method)

            for one_supplier in suppliers:
                # for one_supplier in self.env['res.partner'].sudo().
                # search([('supplier', '=', True),('utili_typ', 'in', ['gas_elec_both'])]):
                supplier_data.append({
                    'Supplier': one_supplier.name
                })
                plans_elec = []
                plans_gas = []
                for one_plan in one_supplier.electric_plans_info_line:
                    one_plan_dict = {}
                    if one_plan.duration:
                        one_plan_dict['Duration'] = one_plan.duration
                    if one_plan.plan_type:
                        one_plan_dict['PlanType'] = one_plan.plan_type
                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                        one_plan_dict['Uplift'] = one_plan.uplift_val
                    if one_plan_dict:
                        plans_elec.append(one_plan_dict)

                for one_plan in one_supplier.gass_plans_info_line:
                    one_plan_dict = {}
                    if one_plan.duration:
                        one_plan_dict['Duration'] = one_plan.duration
                    if one_plan.plan_type:
                        one_plan_dict['PlanType'] = one_plan.plan_type
                    if one_plan.uplift_val and one_plan.uplift_val <= self.uplift_value:
                        one_plan_dict['Uplift'] = one_plan.uplift_val
                    if one_plan_dict:
                        plans_gas.append(one_plan_dict)

                if plans_elec:
                    supp_elec_plan_dur_dict.append({
                        'Supplier': one_supplier.supplier_name_elec,
                        'Plans': plans_elec,
                    })
                    # print '-----supplier name ::>>>>', one_supplier.supplier_name_elec
                if plans_gas:
                    supp_gas_plan_dur_dict.append({
                        'Supplier': one_supplier.supplier_name_gas,
                        'Plans': plans_gas,
                    })

            meter_data_line = self.env['meter.data.line'].browse(self._context['active_id'])
            for meter in self.meter_data_id:
                if meter.contract_id:
                    print ("-----meter contract id ::>>>>", meter.contract_id)
                    for contract in meter.contract_id:
                        current_date = datetime.strftime(datetime.now(), '%Y-%m-%d')
                        # print '-----printed new _date suvbtracted:::>>>>', current_date
                        # print '----contract start date ::>>>>', contract.start_date
                        date_subtracted = (fields.Date.from_string(contract.start_date) - fields.Date.from_string(
                            current_date)).days
                        # print '----subtracted date printed ::>>>>', date_subtracted

                        if contract.contract_type_id.name == 'Renewal':
                            if self.utility_type == 'ele':
                                call_contract_renewal_elec_current_supp_prices = self.contract_renewal_elec_current_supp_prices()
                                print("---contract renewal current supplier electric-->>>")
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }

                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        # "CurrentSupplier":meter.sale_order_line_id.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }
                                # print '------current supplier elec--:::>>>>', contract.supplier_for_docusign
                                # print '------values----',values
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                # print dict(response)
                                # self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"]["Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                        if elec_gas_pricing_tool_val[
                                            'supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(
                                                elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--", pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                            # print "---supplier ref:>>>>", supplier_ref_method
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetElectricRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                call_contract_renewal_gas_current_supp_prices = self.contract_renewal_gas_current_supp_prices()
                                print("----contract renewal current supplier gas rate>>>>>>")
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {"ContactName": contract.partner_id.name,
                                                    "Telephone": {
                                                        "Number": contract.partner_id.phone},
                                                    "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        # "CurrentSupplier":meter.sale_order_line_id.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }

                                # print ('---current supply gas-----:::>>>>',
                                # meter.sale_order_line_id.supplier_id.ud_supplier_name)
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)

                                # print "---response --------rr---", type(response)
                                # print "---response --------rr---",response
                                # self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetGasRatesResult") and response["GetGasRatesResult"][
                                    "Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(
                                                elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--",pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetGasRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
                        elif contract.contract_type_id.name == 'Acquisition':
                            # for contract in meter.sale_order_line_id.order_id.partner_id.contract_line:
                            if self.utility_type == 'ele':
                                call_contract_renewal_elec_previous_supp_prices = \
                                    self.contract_renewal_elec_previous_supp_prices()
                                print ("----contract acquisition---previous supplier elec rates ;;;>>>>")
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }

                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        # "CurrentSupplier":meter.sale_order_line_id.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }

                                # print '------current supplier elec--:::>>>>', contract.supplier_for_docusign

                                # print '------values----',values
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                # print dict(response)
                                # self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"]["Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })

                                        if elec_gas_pricing_tool_val[
                                            'supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(
                                                elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--", pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetElectricRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                call_contract_renewal_gas_previous_supp_prices = self.contract_renewal_gas_previous_supp_prices()
                                print ("----contract acquisition---previous supplier gas rates ;;;>>>>")
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }
                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        # "CurrentSupplier": 'British Gas',
                                        # "CurrentSupplier":meter.sale_order_line_id.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }

                                # print '---current supply gas-----:::>>>>',meter.
                                # sale_order_line_id.supplier_id.ud_supplier_name
                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                # print "---response --------rr---",response
                                # self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetGasRatesResult") and \
                                                response["GetGasRatesResult"]["Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(
                                                elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--",pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetGasRatesResult"), indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
                        else:
                            if self.utility_type == 'ele':
                                print ("----co----not renewal either acquisition electric rates;;;>>>>")
                                mpan_code = str(self.mpan_code).replace('-', '')
                                electric_supply = {
                                    "DayConsumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPANTop": mpan_code[0:8],
                                    "MPANBottom": mpan_code[8:21],
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractEndDate": str(self.contract_start_date),
                                    "NoOfPrompts": 1,
                                    "NightConsumption": {"Amount": 0, "Type": 'Night'},
                                    "WendConsumption": {"Amount": 0, "Type": 'Weekend'},

                                }

                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "ElectricSupply": electric_supply,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_elec_plan_dur_dict,

                                    },

                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": False},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "complete"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": True},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": False},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }

                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST',
                                                           'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)
                                # print "---response --------rr---", response

                                # print dict(response)
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetElectricRatesResult") and \
                                                response["GetElectricRatesResult"]["Rates"] != []:
                                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if elec_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': elec_supp_detail.get("Supplier")
                                            })
                                        if elec_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': elec_supp_detail.get("Uplift")
                                            })
                                        if elec_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': elec_supp_detail.get("StandingCharge")
                                            })
                                        if elec_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if elec_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': elec_supp_detail.get("NightUnitrate")
                                            })
                                        if elec_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': elec_supp_detail.get("WendUnitrate")
                                            })
                                        if elec_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': elec_supp_detail.get("Term")
                                            })
                                        if elec_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': elec_supp_detail.get("PlanType")
                                            })
                                        if elec_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': elec_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if elec_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': elec_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                                # [41:46]
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })
                                                # [75:83]
                                        elif self.smart_meter_rate_selec == 'no':
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': elec_supp_detail.get("SC")
                                                })
                                            if elec_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': elec_supp_detail.get("Fits")
                                                })

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(
                                                elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--", pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetElectricRatesResult"),
                                            indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }

                            elif self.utility_type == 'gas':
                                print ("----co--- not renewal nor acquisition gas rates;;;>>>>")
                                mpan_code = str(self.mpan_code).replace('-', '')
                                gas_supply = {
                                    "Consumption": {"Amount": self.day_consumption, "Type": 'Day'},
                                    "MPR": mpan_code,
                                    "SmartMeter": self.smart_meter_rate,
                                    "ContractRenewalDate": str(self.contract_start_date),

                                }

                                # for one_uplift in list(np.arange(0.0, self.uplift_value, 0.1)):
                                values = {
                                    "quoteDetails": {
                                        "Contact": {
                                            "ContactName": contract.partner_id.name,
                                            "Telephone": {
                                                "Number": contract.partner_id.phone},
                                            "EmailAddress": contract.partner_id.email},
                                        "SecurityDetails": security_details,
                                        "GasSupply": gas_supply,
                                        "PostCode": self.post_code,
                                        "Uplift": self.uplift_value,
                                        # "Renewal": self.is_contract_renewal,
                                        "CurrentSupplier": contract.supplier_id.ud_supplier_name,
                                        "COT": False,
                                        "PaymentMethod": payment_method,
                                        "QuoteDefinitions": supp_gas_plan_dur_dict
                                    },
                                    "Settings": [
                                        {"key": "BG_WithoutSC", "value": False},
                                        {"key": "Corona_FixedRates", "value": False},
                                        {"key": "Corona_AllInclusiveRates", "value": False},
                                        {"key": "Dong_SCType", "value": "normal"},
                                        {"key": "CreditScore", "value": 50},
                                        {"key": "EDFSME_RateType", "value": "Low Price/Low Commission"},
                                        {"key": "EDFSME_OnePlusYear", "value": True},
                                        {"key": "EON_ExcludeDiscounts", "value": True},
                                        {"key": "Gazprom_LowSC", "value": False},
                                        {"key": "Gazprom_WithSC", "value": False},
                                        {"key": "Haven_ProductType", "value": "standard"},
                                        {"key": "Haven_Amr_Rates", "value": False},
                                        {"key": "Opus_BaseRates", "value": False},
                                        {"key": "Opus_GasWithSC", "value": False},
                                        {"key": "OVO_GreenRates", "value": False},
                                        {"key": "SSE_AmrRates", "value": False},
                                        {"key": "SSE_IncludeFitsAndDDDiscount", "value": True},
                                        {"key": "TGP_ReducedYearMonths", "value": 0},
                                        {"key": "TGP_GasWithSC", "value": True},
                                        {"key": "TGP_ElecBasketRates", "value": False},
                                        {"key": "TGP_GasBasketRates", "value": False},
                                        {"key": "UGP_LowCreditRates", "value": False},
                                        {"key": "UGP_PubRates", "value": False},
                                        {"key": "YGP_CommsType", "value": "Monthly"},
                                        {"key": "YGP_SCharge", "value": False}
                                    ]
                                }

                                http = urllib3.PoolManager()
                                encoded_data = json.dumps(values).encode('utf-8')
                                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                                           body=encoded_data,
                                                           headers={'Content-Type': 'application/json'})
                                response = json.loads(data_encode.data.decode('utf-8'))
                                response = dict(response)

                                # print "---response --------rr---", type(response)
                                # print "---response --------rr---",response
                                self.write({'pricing_tool_ids': [(5, 0)]})
                                if response and response.get("GetGasRatesResult") and \
                                                response["GetGasRatesResult"]["Rates"] != []:
                                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                                        elec_gas_pricing_tool_val = {
                                            'pricing_tool_id': self.id
                                        }
                                        if gas_supp_detail.get("Supplier"):
                                            elec_gas_pricing_tool_val.update({
                                                'supplier': gas_supp_detail.get("Supplier")
                                            })
                                        if gas_supp_detail.get("Uplift"):
                                            elec_gas_pricing_tool_val.update({
                                                'uplift_value': gas_supp_detail.get("Uplift")
                                            })
                                        if gas_supp_detail.get("StandingCharge"):
                                            elec_gas_pricing_tool_val.update({
                                                'standing_charge': gas_supp_detail.get("StandingCharge")
                                            })
                                        if gas_supp_detail.get("DayUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'primary_rate': dayunit_rate
                                            })
                                        if gas_supp_detail.get("NightUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'secondary_rate': gas_supp_detail.get("NightUnitrate")
                                            })
                                        if gas_supp_detail.get("WendUnitrate"):
                                            elec_gas_pricing_tool_val.update({
                                                'tertiary_rate': gas_supp_detail.get("WendUnitrate")
                                            })
                                        if gas_supp_detail.get("Term"):
                                            elec_gas_pricing_tool_val.update({
                                                'duration_term': gas_supp_detail.get("Term")
                                            })
                                        if gas_supp_detail.get("PlanType"):
                                            elec_gas_pricing_tool_val.update({
                                                'plan_type': gas_supp_detail.get("PlanType")
                                            })
                                        if gas_supp_detail.get("AnnualPriceInclusive"):
                                            elec_gas_pricing_tool_val.update({
                                                'annual_price_inclusive': gas_supp_detail.get(
                                                    "AnnualPriceInclusive")
                                            })
                                        if gas_supp_detail.get("Ref"):
                                            elec_gas_pricing_tool_val.update({
                                                'validation_ref': gas_supp_detail.get("Ref")
                                            })
                                        if self.smart_meter_rate_selec == 'yes':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })
                                        elif self.smart_meter_rate_selec == 'no':
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'extra_info': gas_supp_detail.get("SC")
                                                })
                                            if gas_supp_detail.get("ExtraInfo"):
                                                elec_gas_pricing_tool_val.update({
                                                    'fit_rate': gas_supp_detail.get("Fits")
                                                })

                                        if elec_gas_pricing_tool_val['supplier'] == 'Opus' and date_subtracted > 240:
                                            pass
                                        else:
                                            pricing_tool = self.env['pricing.tool'].create(
                                                elec_gas_pricing_tool_val)
                                            # print "----pricing_tool--",pricing_tool
                                            # supplier_ref_method = self.supplier_ref_get_value()
                                else:
                                    raise ValidationError(
                                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                                        '\n ######################\n %s' % json.dumps(
                                            response.get("GetGasRatesResult"), indent=3))

                                return {
                                    'name': 'Quote',
                                    'type': 'ir.actions.act_window',
                                    # 'view_type': 'form',
                                    'view_mode': 'form',
                                    'res_model': 'meter.quote.pricing.wiz',
                                    'res_id': self.id,
                                    'target': 'new',
                                }
                else:
                    raise ValidationError("Need to Create atleast one Contract Line", "To Complete this proccess.")


class PricingTool(models.TransientModel):
    _name = 'pricing.tool'
    _description = "Pricing Tool"

    pricing_tool_id = fields.Many2one('meter.quote.pricing.wiz', 'Pricing Tool', readonly=True)
    meter_data_id = fields.Many2one('meter.data.line', related='pricing_tool_id.meter_data_id',
                                    string='Meter Data Line')
    supplier = fields.Char('Supplier')
    uplift_value = fields.Float('Uplift Value', digits=(14, 5))
    annual_price_inclusive = fields.Char('Annual Price Inclusive CCL')
    standing_charge = fields.Float('Standing Charge', digits=(14, 5))
    primary_rate = fields.Float('Primary Rate', digits=(14, 5))
    secondary_rate = fields.Float('Secondary Rate', digits=(14, 5))
    tertiary_rate = fields.Float('Eve/WE Rate', digits=(14, 5))
    day_consumption = fields.Float('Usage')
    duration_term = fields.Integer('Term')
    plan_type = fields.Char('PlanType')
    extra_info = fields.Char('Quarterly Charge/Smart Meter')
    fit_rate = fields.Float('FiT Rate', digits=(14, 5))
    compare_price = fields.Boolean("Select Price")
    validation_ref = fields.Char('Validation Ref')

    
    def update_api(self):
        for rec in self:
            udicore_api = self.env['udicore.api.menu'].search([])

            if not udicore_api:
                raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
            for udcore in udicore_api:
                security_details = {"LicenceCode": udcore.licence_code, "mascaradeuser": udcore.mascarade_user}
            pricing_tool = rec.pricing_tool_id.pricing_tool_ids
            # for price in pricing_tool:
            day_consumption = rec.pricing_tool_id.day_consumption
            mpan_code = rec.pricing_tool_id.mpan_code

            payment_method = ''
            if rec.pricing_tool_id.payment_method == 'dir_deb_mont':
                payment_method = 'Direct Debit (Monthly)'
            elif rec.pricing_tool_id.payment_method == 'dir_deb_quat':
                payment_method = 'Direct Debit (Quaterly)'
            else:
                payment_method = 'Cash Cheque'
            print ('---print payment method:::>>>', payment_method)

            if rec.pricing_tool_id.utility_type == 'ele':
                values = {
                    "quoteDetails": {
                        "SecurityDetails": security_details,
                        "ElectricSupply": {
                            "DayConsumption": {"Amount": day_consumption, "Type": "Day"},
                            "MPANTop": mpan_code[0:8],
                            "MPANBottom": mpan_code[8:21],
                            "SmartMeter": rec.pricing_tool_id.smart_meter_rate,
                            "ContractEndDate": str(rec.pricing_tool_id.contract_start_date)
                        },
                        "Uplift": rec.uplift_value,
                        # "Renewal": rec.pricing_tool_id.is_contract_renewal,
                        "PaymentMethod": payment_method,
                        "QuoteDefinitions": [
                            {"Supplier": rec.supplier, "Plans": [{"Duration": rec.duration_term}]},
                        ]
                    }
                }
                http = urllib3.PoolManager()
                encoded_data = json.dumps(values).encode('utf-8')
                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                           body=encoded_data, headers={'Content-Type': 'application/json'})
                print ("----print request ::>>>>>", data_encode)
                response = json.loads(data_encode.data.decode('utf-8'))
                response = dict(response)

                if response and response.get("GetElectricRatesResult") and response["GetElectricRatesResult"]["Rates"]:
                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                        dayunit_rate = elec_supp_detail.get("DayUnitrate").replace(',', '')
                        rec.uplift_value = elec_supp_detail.get("Uplift")
                        rec.standing_charge = elec_supp_detail.get("StandingCharge")
                        rec.primary_rate = dayunit_rate
                        rec.secondary_rate = elec_supp_detail.get("NightUnitrate")
                        rec.tertiary_rate = elec_supp_detail.get("WendUnitrate")
                        rec.duration_term = elec_supp_detail.get("Term")
                        rec.plan_type = elec_supp_detail.get("PlanType")
                        rec.annual_price_inclusive = elec_supp_detail.get("AnnualPriceInclusive")
                        rec.extra_info = elec_supp_detail.get("SC")
                        rec.fit_rate = elec_supp_detail.get("Fits")
                        # [41:46][75:83]

            elif rec.pricing_tool_id.utility_type == 'gas':
                values = {
                    "quoteDetails": {
                        "SecurityDetails": security_details,
                        "GasSupply": {
                            "Consumption": {"Amount": day_consumption, "Type": "Day"},
                            "MPR": mpan_code,
                            "SmartMeter": rec.pricing_tool_id.smart_meter_rate,
                            "ContractRenewalDate": str(rec.pricing_tool_id.contract_start_date)
                        },
                        "PostCode": rec.pricing_tool_id.post_code,
                        "Uplift": rec.uplift_value,
                        # "Renewal": rec.pricing_tool_id.is_contract_renewal,
                        "PaymentMethod": payment_method,
                        "QuoteDefinitions": [
                            {"Supplier": rec.supplier, "Plans": [{"Duration": rec.duration_term}]},
                        ]
                    }
                }
                http = urllib3.PoolManager()
                encoded_data = json.dumps(values).encode('utf-8')
                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                           body=encoded_data, headers={'Content-Type': 'application/json'})
                print ("----print request ::>>>>>", data_encode)
                response = json.loads(data_encode.data.decode('utf-8'))
                response = dict(response)

                if response and response.get("GetGasRatesResult") and response["GetGasRatesResult"]["Rates"]:
                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                        dayunit_rate = gas_supp_detail.get("DayUnitrate").replace(',', '')
                        rec.uplift_value = gas_supp_detail.get("Uplift")
                        rec.standing_charge = gas_supp_detail.get("StandingCharge")
                        rec.primary_rate = dayunit_rate
                        rec.secondary_rate = gas_supp_detail.get("NightUnitrate")
                        rec.tertiary_rate = gas_supp_detail.get("WendUnitrate")
                        rec.duration_term = gas_supp_detail.get("Term")
                        rec.plan_type = gas_supp_detail.get("PlanType")
                        rec.annual_price_inclusive = gas_supp_detail.get("AnnualPriceInclusive")
                        rec.extra_info = gas_supp_detail.get("SC")
                        rec.fit_rate = gas_supp_detail.get("Fits")
                        # [41:46][75:83]

            # rec.annual_price_inclusive = 10000
            return {
                'name': 'Quote',
                'type': 'ir.actions.act_window',
                # 'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'meter.quote.pricing.wiz',
                'res_id': self.pricing_tool_id.id,
                'target': 'new',
                'context': {'default_pricing_tool_ids': [(6, 0, pricing_tool.ids)]}
            }

    
    def apply_prices(self):
        supplier_obj = self.env['res.partner']
        supplier_ids = supplier_obj.search([('ud_supplier_name', 'ilike', self.supplier), ('supplier', '=', True)])
        print ('-----new supplpier idsi like????????', supplier_ids)
        # zero_value = 0

        for meter in self.meter_data_id:
            uplift = 0
            if self.uplift_value != 0:
                uplift = self.uplift_value
            else:
                uplift = self.pricing_tool_id.uplift_value
            meter.supplier = self.supplier
            meter.uplift_value = self.uplift_value
            if self.pricing_tool_id.smart_meter_rate_selec == 'yes':
                meter.standing_charge_sell = self.extra_info
            elif self.pricing_tool_id.smart_meter_rate_selec == 'no':
                meter.standing_charge_sell = self.extra_info
            else:
                meter.standing_charge_sell = self.standing_charge
            meter.primary_rate_sell = self.primary_rate
            meter.secondary_rate_sell = self.secondary_rate
            meter.tertiary_rate_sell = self.tertiary_rate
            meter.fit_rate_sell = self.fit_rate
            meter.fit_rate = self.fit_rate
            meter.product_uom_qty = self.pricing_tool_id.day_consumption
            if meter.so_boolean:
                meter.contract_id.sale_year_duration = str(self.duration_term)
                # meter.sale_order_line_id.end_date = end_date
                meter.contract_id.sale_start_date = self.pricing_tool_id.contract_start_date
                meter.contract_id.sale_supplier_id = supplier_ids.ids[0]
                meter.contract_id.sale_uplift_value = uplift
                meter.contract_id.sale_broker_uplift_value = uplift
                # sale_order_line_id.order_id.contract_line
                sale_end_date = datetime.strptime(str(self.pricing_tool_id.contract_start_date), "%Y-%m-%d") + \
                                relativedelta(years=+int(self.duration_term), days=-1)
                meter.contract_id.write({'sale_year_duration': str(self.duration_term),
                                         'sale_end_date': sale_end_date.strftime('%Y-%m-%d')})
            elif meter.co_boolean:
                meter.supplier_id = self.supplier
                meter.contract_id.start_date = self.pricing_tool_id.contract_start_date
                meter.contract_id.supplier_id = supplier_ids.ids[0]
                print("----supplier ::>>>>>>>", self.supplier)
                if self.supplier == 'Engie':
                    meter.contract_id.valida_ref_engie = self.validation_ref
                else:
                    meter.contract_id.valida_ref_engie = ''
                meter.contract_id.supplier_for_docusign = self.supplier
                meter.contract_id.supplier_plan_type = self.plan_type
                # for main meter data line form
                if self.pricing_tool_id.smart_meter_rate_selec == 'yes':
                    meter.contract_id.standing_charge_sell = self.extra_info
                elif self.pricing_tool_id.smart_meter_rate_selec == 'no':
                    meter.contract_id.standing_charge_sell = self.extra_info
                else:
                    meter.contract_id.standing_charge_sell = self.standing_charge
                meter.contract_id.primary_rate_sell = self.primary_rate
                meter.contract_id.secondary_rate_sell = self.secondary_rate
                meter.contract_id.tertiary_rate_sell = self.tertiary_rate
                meter.contract_id.fit_rate_sell = self.fit_rate
                meter.contract_id.fit_rate = self.fit_rate

                meter.contract_id.sale_year_duration = str(self.duration_term)
                meter.contract_id.sale_start_date = self.pricing_tool_id.contract_start_date
                meter.contract_id.start_date = self.pricing_tool_id.contract_start_date
                end_date = datetime.strptime(str(self.pricing_tool_id.contract_start_date),
                                             "%Y-%m-%d") + \
                           relativedelta(years=+int(self.duration_term),
                                         days=-1)
                meter.contract_id.sale_end_date = str(end_date)
                meter.contract_id.sale_end_date = str(end_date)
                print ('---meter contract end date ::>>>>', meter.contract_id.end_date)
                meter.contract_id.sale_supplier_id = supplier_ids.ids[0]
                meter.contract_id.uplift_value = uplift
                meter.contract_id.broker_uplift = uplift
                meter.contract_id.sale_uplift_value = uplift
                meter.contract_id.sale_broker_uplift_value = uplift

                comm_pool = self.env['contract.commission.confi']
                if not self.pricing_tool_id.contract_start_date and self.duration_term:
                    return {'value': {'end_date': False}}

                if self.pricing_tool_id.contract_start_date and self.duration_term:

                    commi_year = comm_pool.search([('year_duration', '=', self.duration_term),

                                                   ('external_broker', '=', False)])
                    end_date = datetime.strptime(str(self.pricing_tool_id.contract_start_date), "%Y-%m-%d") + \
                               relativedelta(years=+int(self.duration_term), days=-1)
                    for comm in commi_year:
                        meter.contract_id.write({
                            'year_duration': str(self.duration_term),
                            'end_date': end_date.strftime('%Y-%m-%d'),
                            'commi_year_id': comm and comm.id,
                            'dummy_commi_year_id': comm and comm.id,
                            'dummy_commission_percentage': comm and comm.percentage,
                            'commission_percentage': comm and comm.percentage,

                        })
        return True

# supplier_ref = fields.Char('Supplier Ref')
