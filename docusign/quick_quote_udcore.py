# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import json
import urllib3
import time
from urllib.parse import urlencode


class QuickQuoteUdcore(models.TransientModel):
    _name = 'quick.quote.udcore'
    _description = "Quick Quote Udcore"

    day_consumption = fields.Float('Usage')
    contract_start_date = fields.Date('Contract Start Date')
    utility_type = fields.Selection([('ele', 'Electricity'), ('gas', 'GAS')], string='Utility Type')
    payment_method = fields.Selection([('dir_deb_mont', 'Direct Debit (Monthly)'),
                                       ('dir_deb_quat', 'Direct Debit (Quaterly)'),
                                       ('cash_cheq', 'Cash Cheque')], string='Payment Method')
    quick_quote_tool_ids = fields.One2many('quick.quote.tool', 'quick_quote_id', 'Pricing Tool')
    uplift_value = fields.Float('Uplift Value', digits=(14, 5))
    mpan_code = fields.Char('MPAN / MPR')
    post_code = fields.Char('PostCode')
    is_contract_renewal = fields.Boolean('Renewal')
    smart_meter_rate = fields.Boolean('Smart')
    smart_meter_rate_selec = fields.Selection([('yes', 'Yes'), ('no', 'No'), ('normal', 'NormalRate')],
                                              string='Smart Meter')
    current_supplier_id = fields.Many2one('res.partner', string='Current Supplier', domain=[('supplier', '=', True)])
    email = fields.Char('Email')

    
    def get_supplier_rates(self):

        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            SecurityDetails = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
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
            # for meter in meter_data_line:
            #     for sale in meter.sale_order_line_id:
            paymentmethod = ''
            if self.payment_method == 'dir_deb_mont':
                paymentmethod = 'Direct Debit (Monthly)'
            if self.payment_method == 'dir_deb_quat':
                paymentmethod = 'Direct Debit (Quaterly)'
            if self.payment_method == 'cash_cheq':
                paymentmethod = 'Cash Cheque'

            if self.utility_type == 'ele':
                print ("----Electric Rates;;;>>>>")
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
                            "ContactName": False,
                            "Telephone": {
                                "Number": False},
                            "EmailAddress": False},
                        "SecurityDetails": SecurityDetails,
                        "ElectricSupply": electric_supply,
                        "Uplift": self.uplift_value,
                        "Renewal": self.is_contract_renewal,
                        # "CurrentSupplier": 'British Gas',
                        "CurrentSupplier": self.current_supplier_id.ud_supplier_name,
                        "COT": False,
                        "PaymentMethod": paymentmethod,
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

                # print ('------current supplier elec--:::>>>>', contract.supplier_for_docusign)

                # print ('------values----',values)
                http = urllib3.PoolManager()
                encoded_data = json.dumps(values).encode('utf-8')
                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/electricprices',
                                           body=encoded_data, headers={'Content-Type': 'application/json'})
                print ("----print request ::>>>>>", data_encode)
                response = json.loads(data_encode.data.decode('utf-8'))
                print ("----dataencodeprinted::>>>>>>>", data_encode)

                # print ("---response --------rr---", response)
                response = dict(response)
                # print ("---response --------rr---", response)

                # print (dict(response))
                self.write({'quick_quote_tool_ids': [(5, 0)]})
                if response and response.get("GetElectricRatesResult") and \
                                response["GetElectricRatesResult"]["Rates"] != []:
                    for elec_supp_detail in response["GetElectricRatesResult"]["Rates"]:
                        elec_gas_pricing_tool_val = {
                            'quick_quote_id': self.id
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

                        # print ("---one_pricing_tool_val--", elec_gas_pricing_tool_val)

                        quote_tool = self.env['quick.quote.tool'].create(elec_gas_pricing_tool_val)
                        # print ("----pricing_tool--", quote_tool)
                else:
                    raise ValidationError(
                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                        '\n ######################\n %s' % json.dumps(
                            response.get("GetElectricRatesResult"),
                            indent=3))

                return {
                    'name': 'Quick Quote',
                    'type': 'ir.actions.act_window',
                    # # 'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'quick.quote.udcore',
                    'res_id': self.id,
                    'target': 'new',
                }

            elif self.utility_type == 'gas':
                print ("----Gas Rates;;;>>>>")
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
                            "ContactName": False,
                            "Telephone": {
                                "Number": False},
                            "EmailAddress": False},
                        "SecurityDetails": SecurityDetails,
                        "GasSupply": gas_supply,
                        "PostCode": self.post_code,
                        "Uplift": self.uplift_value,
                        "Renewal": self.is_contract_renewal,
                        # "CurrentSupplier": 'British Gas',
                        "CurrentSupplier": self.current_supplier_id.ud_supplier_name,
                        "COT": False,
                        "PaymentMethod": paymentmethod,
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

                # print ('---current supply gas-----:::>>>>',self.current_supplier_id.ud_supplier_name)
                http = urllib3.PoolManager()
                encoded_data = json.dumps(values).encode('utf-8')
                data_encode = http.request('POST', 'https://udcoreapi.co.uk/Service.svc/web/gasprices',
                                           body=encoded_data, headers={'Content-Type': 'application/json'})
                print ("----print request ::>>>>>", data_encode)
                response = json.loads(data_encode.data.decode('utf-8'))
                print ("----dataencodeprinted::>>>>>>>", data_encode)
                response = dict(response)
                # print ("---response --------rr---", type(response))
                # print ("---response --------rr---",response)
                self.write({'quick_quote_tool_ids': [(5, 0)]})
                if response and response.get("GetGasRatesResult") and response["GetGasRatesResult"]["Rates"] != []:
                    for gas_supp_detail in response["GetGasRatesResult"]["Rates"]:
                        elec_gas_pricing_tool_val = {
                            'quick_quote_id': self.id
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

                        # print ("---one_pricing_tool_val--",elec_gas_pricing_tool_val)

                        quote_tool = self.env['quick.quote.tool'].create(elec_gas_pricing_tool_val)
                        # print ("----pricing_tool--",quote_tool)
                else:
                    raise ValidationError(
                        'Check the "Message","Error Details"\n & "FooterNotes" Below: '
                        '\n ######################\n %s' % json.dumps(
                            response.get("GetGasRatesResult"), indent=3))

                return {
                    'name': 'Quick Quote',
                    'type': 'ir.actions.act_window',
                    # # 'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'quick.quote.udcore',
                    'res_id': self.id,
                    'target': 'new',
                }

    @api.onchange('smart_meter_rate_selec')
    def _onchange_condition(self):
        if self.smart_meter_rate_selec == 'yes':
            self.smart_meter_rate = True
        else:
            self.smart_meter_rate = False


class QuickQuoteTool(models.TransientModel):
    _name = 'quick.quote.tool'
    _description = "Quick Quote Tool"

    quick_quote_id = fields.Many2one('quick.quote.udcore', 'Quick Quote Tool', readonly=True)
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
    fit_rate = fields.Float('FiT Rate')
    compare_price = fields.Boolean('Price Compare')
