# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta
import time
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import json
import requests
from dateutil.relativedelta import relativedelta


class SendUdcoreDocusign(models.TransientModel):
    _name = 'send.udcore.docusign'
    _description = "Send Udcore Docusign"

    email = fields.Char('Email')

    # @api.model
    # def default_get(self, fields):
    #     res = super(SendUdcoreDocusign, self).default_get(fields)
    #     print ('contextttt::>>', self._context)
    #     if self._context and self._context['active_id']:
    #         partner_email = self.env['res.contract'].browse(self._context['active_id'])
    #         print ('------partner email:::>>>>>', partner_email.partner_id.email)
    #         email = ''
    #         partners = []
    #         for part in partner_email.partner_id:
    #             email = part.email
    #             if part.email:
    #                 partners.append(part.id)
    #
    #         # res['partners'] = partners or False
    #         res['email'] = email or False
    #         if not res['email']:
    #             raise ValidationError(("Please complete partner's "
    #                                    "informations & Email ,Partner's Email is Required."))
    #
    #     return res

    
    def send_docusign(self):
        udicore_api = self.env['udicore.api.menu'].search([])
        if not udicore_api:
            raise ValidationError("Please enter the Licencecode and Mascaradeuse in udicore menu")
        for rec in udicore_api:
            security_details = {"LicenceCode": rec.licence_code, "mascaradeuser": rec.mascarade_user}
            contract_form = self.env['res.contract'].browse(self._context['active_id'])
            company_control = "Dernetz"
            print ('---active id contract form printed :>:>>>>>', contract_form)
            for contract in contract_form:
                for meter in contract.meter_data_id:
                    mpan_code = str(meter.mpan_code).replace('-', '')
                    payment_type = ''
                    if contract.payment_type_id and contract.payment_type_id.name == 'DD':
                        print ('-------paymenttyopeid00-------', contract.payment_type_id.name)
                        payment_type = 'Direct Debit'
                        print ('------print variable-----????????', payment_type)
                    elif contract.payment_type_id and contract.payment_type_id.name in ['Cheque', 'CC']:
                        print ('-------paymenttyopeid00-------', contract.payment_type_id.name)
                        payment_type = 'cash/cheque'

                    # start_date_npower = str(datetime.strftime(
                    #     datetime.strptime(contract.start_date, '%Y-%m-%d').date() + \
                    #     relativedelta(contract.year_duration, days=-1), '%Y-%m-%d'))
                    start_date_npower = datetime.strptime(str(contract.start_date), "%Y-%m-%d").date() + \
                           relativedelta(contract.year_duration,
                                         days=-1)
                    print ('---start date npower printed ::>>>>>', start_date_npower)

                    # dob_director = contract.partner_id.child_ids[0].birth_date
                    # print ("-----date of brith::>>>>>>", dob_director)

                    print ('--- partner category id name ::>>>>>', contract.partner_id.category_id.name)
                    print ('--- print bank zip from partner::::>>>>>', contract.partner_id.bank_ids.bank_id.zip)
                    print ('--- print company nyumber from partner::::>>>>>', contract.partner_id.company_number)
                    print ('---prijt meter ::>>>', meter)
                    print ('---prijt meter kva charge sell::>>>', meter.kva_charge_sell)
                    maindetails_default = [
                        {"Key": "new supplier electricity", "Value": contract.supplier_for_docusign},
                        {"Key": "new supplier gas", "Value": contract.supplier_for_docusign},
                        {"Key": "premises name", "Value": contract.partner_id.category_id.name},
                        {"Key": "bank name", "Value": contract.partner_id.bank_ids.bank_name},
                        {"Key": "bank account name", "Value": contract.partner_id.bank_ids.acc_holder_name},
                        {"Key": "account number", "Value": contract.partner_id.bank_ids.acc_number},
                        {"Key": "bank post code", "Value": 'BB96BP'},
                        {"Key": "sort code", "Value": contract.partner_id.bank_ids.bank_bic},
                        {"Key": "company address 1", "Value": contract.partner_id.street},
                        {"Key": "company address 2", "Value": contract.partner_id.street2},
                        {"Key": "company address 3", "Value": contract.partner_id.city},
                        {"Key": "company address 4", "Value": contract.partner_id.zip},
                        # {"Key": "company postcode", "Value":  meterdata.des_partner_id.zip},
                        {"Key": "pub company", "Value": contract.partner_id.name},
                        {"Key": "company number", "Value": contract.partner_id.company_number},
                        {"Key": "business type", "Value": 'Corp'},
                        {"Key": "billing address1", "Value": contract.partner_id.street},
                        {"Key": "billing address2", "Value": contract.partner_id.street2},
                        {"Key": "billing address3", "Value": contract.partner_id.city},
                        {"Key": "billing postcode", "Value": contract.partner_id.zip},
                        {"Key": "ternancy start date", "Value": contract.cot_date or ''},
                        {"Key": "address 1", "Value": contract.partner_id.street},
                        {"Key": "address 2", "Value": contract.partner_id.street2},
                        {"Key": "address 3", "Value": contract.partner_id.city},
                        {"Key": "post code", "Value": contract.partner_id.zip},
                        {"Key": "mobile", "Value": contract.partner_id.mobile},
                        {"Key": "landline", "Value": contract.partner_id.phone},

                        {"Key": "director address1", "Value": contract.des_partner_id.street},
                        {"Key": "director address2", "Value": contract.des_partner_id.street2},
                        {"Key": "director address3", "Value": contract.des_partner_id.city},
                        {"Key": "director postcode", "Value": contract.des_partner_id.zip},
                        {"Key": "job title", "Value": 'Manager'},
                        {"Key": "email", "Value": self.email},
                        {"Key": "elec contract end date", "Value": str(start_date_npower)},
                        {"Key": "gas contract end date", "Value": str(start_date_npower)},
                        {"Key": "gas new contract date", "Value": str(contract.start_date)},
                        {"Key": "elec new contract date", "Value": str(contract.start_date)},
                        {"Key": "kva", "Value": int(meter.kva_charge_sell)},
                        {"Key": "contact name", "Value": 'Hasnain Devjani'},
                    ]

                    usageratesDefault = [
                        {"Key": "daycharge", "Value": meter.primary_rate_sell},
                        {"Key": "nightcharge", "Value": meter.secondary_rate_sell},
                        {"Key": "eveandwendcharge", "Value": meter.tertiary_rate_sell},
                        {"Key": "standing charge", "Value": meter.standing_charge_sell},
                        # {"Key": "dayusage", "Value": contract.usage},
                        {"Key": "nightusage", "Value": 5},
                        {"Key": "eveandwendusage", "Value": 2},

                    ]

                    template_options = [{
                        'PlanType': 'no s/c' or False,
                        'HalfHourly': 'false'
                    }]

                    auxiliarydetailsdata = [
                        {"Key": "SupplierPaymentMethod", "Value": 'DD'},
                        # {"Key": "salesagentname", "Value": contract.user_id.name}

                    ]

                    if contract.supplier_id.ud_supplier_name == 'Npower' and \
                                    contract.contract_type_id.name == 'Renewal':
                        maindetails_default.append({"Key": "current electric supplier 1", "Value": 'Npower'})
                        maindetails_default.append({"Key": "current gas supplier 1", "Value": 'Npower'})
                    else:
                        maindetails_default.append({"Key": "current electric supplier 1",
                                                    "Value": contract.previous_supplier_id.ud_supplier_name})
                        maindetails_default.append(
                            {"Key": "current gas supplier 1", "Value": contract.previous_supplier_id.ud_supplier_name})

                        # print "----templateopttions::::>>>>>",template_options
                        # To Differenciate the mpan and mpr
                    if contract.utility_type_gas_docusign:
                        maindetails_default.append({"Key": "mpr 1", "Value": mpan_code})
                    else:
                        maindetails_default.append({"Key": "mpan top line 1", "Value": mpan_code[0:8]})
                        maindetails_default.append({"Key": "mpan bottom line 1", "Value": mpan_code[8:21]})
                        print ("----bottom line::>>>>>", mpan_code[8:21])
                        print ("----top line::>>>>>", mpan_code[0:8])

                    # TO display conatct name
                    # if contract.supplier_id.ud_supplier_name == 'CNG':
                    #     maindetails_default.append({"Key": "contact name", "Value": contract.partner_id.name})
                    # else:
                    # print '-----contact name if condition<<<<<<<<<<,',contract.des_partner_id.name
                    # maindetails_default.append({"Key": "contact name", "Value": contract.des_partner_id.name})
                    # print '-----contact name hdddddddddddddd,', contract.des_partner_id.name
                    months = 12
                    dur_months = int(contract.year_duration) * int(months)
                    if contract.supplier_for_docusign == 'Opus' and 'SSE':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Dual Energy':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Crown':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'D-ENERGi':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'CNG':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'EDF':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Engie':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Extra Energy':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Gazprom':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Haven':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Hudson Energy':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Scottish Power':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Total Gas And Power':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Utilita':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Yorkshire Gas And Power':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Npower':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    elif contract.supplier_for_docusign == 'Scottish And Southern':
                        maindetails_default.append({"Key": "elec new contract length", "Value": dur_months})
                        maindetails_default.append({"Key": "gas new contract length", "Value": dur_months})
                    else:
                        maindetails_default.append({"Key": "elec new contract length", "Value": contract.year_duration})
                        maindetails_default.append({"Key": "gas new contract length", "Value": contract.year_duration})

                    if not contract.supplier_id.ud_supplier_name == 'Npower':
                        auxiliarydetailsdata.append({"Key": "salesagentname", "Value": contract.user_id.name})
                        # print "-----userid::::>>>>>",contract.user_id.name

                    # payment method condition specially for npower and other in else
                    if not contract.supplier_for_docusign == 'Npower':
                        maindetails_default.append({"Key": "payment method", "Value": 'DD'})

                    meter_details_data = []
                    if contract.supplier_for_docusign == 'Scottish And Southern':
                        meter_details_data.append({"Key": "sc", "Value": meter.standing_charge_sell})
                        meter_details_data.append({"Key": "fits", "Value": meter.fit_rate_sell})
                        meter_details_data.append({"Key": "period", "Value": contract.sse_billing_period})
                        print ('in if condition for period ::>>>>>>>')
                    else:
                        meter_details_data.append({"Key": "sc", "Value": 2})
                        meter_details_data.append({"Key": "fits", "Value": 3})
                        meter_details_data.append({"Key": "period", "Value": 'Monthly'})
                        print ('in else condirion for period ::::>>>>>>>>')

                    if contract.supplier_for_docusign == 'Engie':
                        meter_details_data.append({"Key": "ref", "Value": contract.valida_ref_engie})
                    else:
                        meter_details_data.append({"Key": "ref", "Value": 5})

                    # Commented below birth date code for testing purpose::::>>

                    if contract.supplier_for_docusign == 'British Gas':
                        maindetails_default.append({"Key": "date of birth", "Value": '2018-08-27'})
                    else:
                        maindetails_default.append({"Key": "director dob", "Value": '2018-08-27'})

                    usage_with_duration = int(contract.usage) * int(contract.year_duration)
                    if contract.supplier_for_docusign == 'Gazprom':
                        usageratesDefault.append({"Key": "dayusage", "Value": usage_with_duration})
                    # elif contract.supplier_for_docusign == 'Scottish And Southern':
                    #     usageratesDefault.append({"Key": "dayusage", "Value": sse_usage})
                    else:
                        usageratesDefault.append({"Key": "dayusage", "Value": contract.usage})

                    postdata = {
                        'docusignDetails': {
                            'ItsAGasContract': contract.utility_type_gas_docusign,
                            'ControlCompanyName': company_control,
                            'MainDetailsData': maindetails_default,
                            'meter_details_data': meter_details_data,
                            'template_options': template_options,
                            'UsageRatesData': usageratesDefault,
                            'SecurityDetails': security_details,
                            'AuxiliaryDetailsData': auxiliarydetailsdata,

                        }
                    }

                    headers = {'content-type': 'application/json; charset=utf-8'}
                    url = 'https://udcoreapi.co.uk/DocusignService.svc/web/senddocusign'

                    data = postdata
                    aa = requests.post(url, data=json.dumps(data), headers=headers)
                    # print ('post data in api::>>>>',data)
                    # print ("-----------------content-------------", aa.content)
                    # print ("------aa------", aa.json)
                    # print ('-  ------------------',aa)
                    aa = json.loads(aa.text)
                    # print ("-----------------docusignresult-------------", aa.get('SendDocusignResult'))
                    print ("-----------------EnvolopeID-------------", aa.get('SendDocusignResult').get('EnvelopeID'))

                    login_user = self.env.user or self.env['res.users'].browse(self._context['uid'])

                    mail_doc = self.env['docusign.document'].create({
                        # 'email_to': self.recipients_to,
                        'email_to': self.email,
                        'email_from':
                            login_user and login_user.email and
                            login_user.name + ' <' + login_user.email + '>' or False,
                        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'author_id': login_user and login_user.id or False,
                        'res_id':
                            contract or contract.get('active_id', False) and contract['active_id'] or False,
                        'model':
                            contract or contract.get('active_model', False) and contract['active_model'],

                        'subject': 'Dernetz ' + '(Ref ' + contract.contract_name + ')',
                        'partner_ids': [(4, contract.partner_id[0].id, 0)],
                        'partner_id': contract.partner_id[0].id,
                        'contract_id': contract.id,

                    })
                    # try:
                    if aa.get('SendDocusignResult').get('EnvelopeID'):
                        mail_doc.write({'state': 'sent', 'ref_id': aa.get('SendDocusignResult').get('RefID'),
                                        'env_id': aa.get('SendDocusignResult').get('EnvelopeID')})
                        contract.write({'state': 'docusign_pending',
                                        'docusign_sent_datetime': datetime.now(),
                                        'docusign_received': 'Sent',
                                        })
                    else:
                        mail_doc.write({'state': 'fail', 'env_id': ''})
                        # raise Exception('Some of the Dictionaries are Empty Below: %s' % data)
                        raise ValidationError('Fill The Values Which are Mentioned \n  '
                                              'as "false" Below except field "ItsAGasContract": '
                                              '\n -----------------\n %s' % json.dumps(data, indent=3))
