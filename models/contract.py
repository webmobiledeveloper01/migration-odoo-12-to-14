from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import time
import logging
import pytz
# from odoo import osv
# from dateutil.relativedelta import *
# from odoo.addons import decimal_precision as dp

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

_logger = logging.getLogger(__name__)


class ResContractState(models.Model):
    _name = 'res.contract.state'
    _description = "Res Contract State"

    name = fields.Char(
        'Name', size=32, required=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'), ('doc_pending', 'Pending(Admin)'), (
                'docusign_pending', 'Delivered(Docusign)'),
            ('sale_agreed', 'Sale Agreed'), ('confirmed', 'Confirmed'),
            ('accepted', 'Accepted'), ('live', 'LIVE'), ('complete', 'Complete'), (
                'livenocis_scanned', 'LiveNOCIS Scanned'),
            ('payment_confirmed', 'Payment Confirmed'), ('query', 'Query'),
            ('cot_cancelled', 'COT Cancelled'), ('cancelled', 'Cancelled')
        ],
        'Contract State',
        required=True)
    probability = fields.Float(
        'Percentage', required=True)
    description = fields.Text('Description')


class Contract(models.Model):
    _name = 'res.contract'
    _description = 'Contract'
    _rec_name = 'rec_name'
    _inherit = ['mail.thread']

    # 'order_type', 'so_boolean', 'co_boolean'
    @api.depends('sale_name', 'contract_name')
    def _compute_rec_name(self):
        for rec in self:
            # if self.env.context.get('sale_menu', False):
            #     rec.rec_name = rec.sale_name
            #     print ('in if condition sale menu context ::>>>')
            # elif self.env.context.get('contract_menu', False):
            #     rec.rec_name = rec.contract_name
            #     print ('in elif condition contract  menu contextc ::>>>')

            if rec.so_boolean and rec.co_boolean:
                rec.rec_name = rec.contract_name
            elif rec.co_boolean and not rec.so_boolean:
                rec.rec_name = rec.contract_name
            elif rec.so_boolean and not rec.co_boolean:
                rec.rec_name = rec.sale_name
            # else:
            #     rec.rec_name = rec.sale_name

    def get_dynamic_ip(self):
        domain = self.env["ir.config_parameter"].get_param(
            "web.base.url")
        try:
            alias_domain = urlparse.urlsplit(domain).netloc
        except ValueError:
            alias_domain = '88.208.209.80:8069'
        return alias_domain

    @api.depends('usage', 'supplier_uplift')
    def _calulate_supplier_commission(self):
        for line in self:
            line.supplier_commission = (
                line.usage * line.supplier_uplift) / 100

    def _get_meter_data_line_code(self):
        if self.utility_type == 'ele' and self.meter_data_id:
            self.mpan_code = self.meter_data_id.mpan_code
        elif self.utility_type == 'gas' and self.meter_data_id:
            self.mpan_code = self.meter_data_id.mpr_code

        # meter_data_line_obj = self.env['meter.data.line']
        # for self_obj in self:
        #     meter_ids = meter_data_line_obj.search([('contract_id', '=', self_obj.id)])
        #     if meter_ids:
        #         for meter_line in meter_ids:
        #             if meter_line.mpan_code:
        #                 self_obj.mpan_code_first = \
        #                     self_obj.mpan_code_first or '' + str(meter_line.mpan_code) + '\n'

    @api.depends('broker_commission_first_payment')
    def _calculate_ext_full_commission_total(self):
        for line in self:
            line.external_full_commission = line.broker_commission_first_payment

    @api.depends('external_broker_reconcile_ids')
    def _ext_brokercommission_amount_diff_total(self):
        reconcile_total = 0.0
        for line in self:
            if line.external_broker_reconcile_ids:
                for rec_obj in line.external_broker_reconcile_ids:
                    reconcile_total += rec_obj.comm_amount
            line.ext_brokercommission_amount_total = reconcile_total

    @api.depends('external_broker_reconcile_ids', 'broker_commission_first_payment')
    def _ext_calculate_commission_to_pay(self):
        reconcile_total = 0.0
        for line in self:
            line.ext_commission_to_pay = 0.0
            if line.external_broker_reconcile_ids:
                for rec_obj in line.external_broker_reconcile_ids:
                    reconcile_total += rec_obj.comm_amount
            if line.broker_commission_first_payment:
                line.ext_commission_to_pay = line.external_broker_commission - \
                    line.broker_commission_first_payment - reconcile_total
                # res[line.id] = line.external_full_commission - reconcile_total - line.broker_commission_first_payment
                # print "---external broker commission::>>>>", line.external_broker_commission
                # print "---broker_comission first pay in if condition::>>>>", line.broker_commission_first_payment
                # print "---unadjusted commission::>>>>", line.external_full_commission
                # print "---com amount reconcile total::>>>>", reconcile_total
                # print "res line id in if ::>>>>",res[line.id]
            else:
                # res[line.id] = line.external_full_commission - reconcile_total
                line.ext_commission_to_pay = (line.external_broker_commission - reconcile_total) or \
                    line.external_broker_commission

    @api.depends('start_date', 'end_date', 'categ_id')
    def _calc_alert(self):
        for contract in self:
            if contract.superseded:
                contract.alert = False
                continue
            start = contract.categ_id \
                and contract.categ_id.start or contract.categ_id \
                and contract.categ_id.start or 0.0
            end = contract.categ_id \
                and contract.categ_id.end \
                or contract.categ_id and contract.categ_id.end or 0.0
            if start and end:
                first = datetime.datetime.strptime(contract.end_date,
                                                   '%Y-%m-%d') - \
                    datetime.timedelta(days=int(start))
                second = datetime.datetime.strptime(contract.end_date,
                                                    '%Y-%m-%d') - \
                    datetime.timedelta(days=int(end))
                if datetime.datetime.strptime(time.strftime('%Y-%m-%d'),
                                              '%Y-%m-%d') >= first and \
                    datetime.datetime.strptime(time.strftime('%Y-%m-%d'),
                                               '%Y-%m-%d') <= second:
                    contract.alert = True
                else:
                    contract.alert = False

    def cron_call(self):
        self._context.update({'cron_call': True})
        self._cr.execute(
            "UPDATE res_contract SET days_to_expiry=(end_date - NOW()::date)::int,days_to_loa_expiry=(loa_expiry - NOW()::date)::int WHERE id IN %s",
            (tuple(self.ids),))
        return True

    @api.model
    def cron_contract_alerts(self):
        contract_ids = self.sudo().search([])
        _logger.info(("Cron job start time: \
            %s") % (time.strftime('%Y-%m-%d %H:%M:%S')))
        contract_ids.cron_call()
        _logger.info(("Cron job end time: \
            %s") % (time.strftime('%Y-%m-%d %H:%M:%S')))
        return True

    # @api.model
    # def send_mail_sales_confirmation_letter_sent(self):
    #     contract_ids = self.search(
    #         [('state', '=', 'confirmed'),
    #          ('sale_confirmed_letter_sent', '=', False)])
    #
    #     ir_model_data = self.env['ir.model.data']
    #     if contract_ids:
    #         for contract_id in contract_ids:
    #             email_template_pool = self.env["mail.template"]
    #             context = dict(self._context)
    #             try:
    #                 template_id = \
    #                     ir_model_data.get_object_reference(
    #                         'dernetz',
    #                         'email_template_sale_confirmation_contract')[
    #                         1]
    #             except ValueError:
    #                 template_id = False
    #             if template_id:
    #                 name = ''
    #                 if contract_id.partner_id.child_ids:
    #                     for line in contract_id.partner_id.child_ids:
    #                         if line.type == 'default':
    #                             name = line.name
    #
    #                 summary_table = ''
    #                 summary_table += '''
    #                                         <table width=90%% style="border:none">
    #                                         <tr>
    #                                             <td><b>''' + _("Dear,"
    #                                                            "") + name + '''</b></td>
    #                                         </tr>
    #                                 '''
    #                 strbegin = '''
    #                                     <TD style="border:none">
    #                                     '''
    #                 strend = '''
    #                                     </TD>
    #                                 '''
    #                 msg = '' \
    #                       'You recently agreed a utility contract with one of our energy consultants. ' \
    #                       'Please find attached a letter from us confirming this. ' \
    #                       'If have an questions about this you can contact our customer support team on 01282 610395 ' \
    #                       'or via email by replying to this email - please quote the reference number ' \
    #                       'contained within the letter.'
    #                 summary_table += "<TR>" + strbegin + msg + strend + "</TR>"
    #                 summary_table += "<TR>" + strbegin + 'Thank you.' + strend + "</TR>"
    #                 summary_table += "<TR>" + strbegin + '' + strend + "</TR>"
    #                 summary_table += "<TR>" + strbegin + 'Customer Support Team Dernetz' + strend + "</TR>"
    #                 summary_table += '''</table>'''
    #                 ctx = context.copy()
    #                 ctx.update({'email_content': summary_table})
    #             msg_id = email_template_pool.browse(template_id).with_context(
    #                 ctx).send_mail(
    #                 contract_id.id,
    #                 force_send=False,
    #                 raise_exception=False,
    #             )
    #             if msg_id:
    #                 contract_id.write(
    #                     {'sale_confirmed_letter_sent': True,
    #                      'sale_confirmed_date': time.strftime(
    #                          '%Y-%m-%d %H:%M:%S')})
    #                 query_id = self.env['query.code'].search(
    #                     [('name', '=', 'Admin Confirmed')]
    #                 )
    #                 if not query_id:
    #                     query_id = self.env['query.code'].create(
    #                         {'name': 'Admin Confirmed',
    #                          'code': '72'},
    #                     ).id
    #                 note_vals = {
    #                     'query_code_id': query_id.id or False,
    #                     'user_id': contract_id.user_id and contract_id.user_id.id or False,
    #                     'partner_id': contract_id.partner_id and contract_id.partner_id.id or False,
    #                     'name': 'Confirmation Letter Sent',
    #                     'contract_id': contract_id.id or False
    #                 }
    #                 self.env['general.note'].sudo().create(
    #                     note_vals)
    #     return True

    # @api.model
    # def send_mail_welcome_letter_automation_sent(self):
    #     contract_ids = self.search(
    #         [('state', 'in', ['complete', 'livenocis_scanned',
    #                           'payment_confirmed']),
    #          ('welcome_letter_sent', '=', False)])
    #     ir_model_data = self.env['ir.model.data']
    #     email_template_pool = self.env["mail.template"]
    #     if contract_ids:
    #         for contract_id in contract_ids:
    #             browse_con = contract_id
    #             context = dict(self._context)
    #             try:
    #                 template_id = \
    #                     ir_model_data.get_object_reference(
    #                         'dernetz',
    #                         'email_template_contract_welcome_letter')[
    #                         1]
    #             except ValueError:
    #                 template_id = False
    #             if template_id:
    #                 name = ''
    #                 if browse_con.partner_id.child_ids:
    #                     for line in browse_con.partner_id.child_ids:
    #                         if line.type == 'default':
    #                             name = line.name
    #
    #                 summary_table = ''
    #                 summary_table += '''
    #                                     <table width=90%% style="border:none">
    #                                     <tr>
    #                                         <td><b>''' + _("Dear,"
    #                                                        "") + name + '''</b></td>
    #                                     </tr>
    #                             '''
    #                 strbegin = '''
    #                                 <TD style="border:none">
    #                                 '''
    #                 strend = '''
    #                                 </TD>
    #                             '''
    #                 msg = 'You recently agreed a utility contract with one of our energy consultants.' \
    #                       ' Please find attached a letter from us confirming this. ' \
    #                       'If have an questions about this you can contact our customer support team on 01282 610395 ' \
    #                       'or via email by replying to this email - please quote the reference number ' \
    #                       'contained within the letter.'
    #                 summary_table += "<TR>" + strbegin + msg + strend + "</TR>"
    #                 summary_table += "<TR>" + strbegin + 'Thank you.' + strend + "</TR>"
    #                 summary_table += "<TR>" + strbegin + '' + strend + "</TR>"
    #                 summary_table += "<TR>" + strbegin + 'Customer Support Team Dernetz' + strend + "</TR>"
    #                 summary_table += '''</table>'''
    #                 ctx = context.copy()
    #                 ctx.update({'email_content': summary_table})
    #             email_template_pool.browse(template_id).with_context(
    #                 ctx).send_mail(
    #                 contract_id.id,
    #                 force_send=False,
    #                 raise_exception=False,
    #             )
    #             contract_id.write(
    #                 {'welcome_letter_sent': True,
    #                  'welcome_letter_date': time.strftime(
    #                      '%Y-%m-%d %H:%M:%S')})
    #     return True

    @api.depends('categ_id', 'end_date')
    def _set_alert_no(self):
        for contract in self:
            if contract.end_date:
                trigger_date = \
                    (datetime.strptime(str(contract.end_date), '%Y-%m-%d') -
                     datetime.today()).days
                if contract.categ_id and contract.categ_id.alert_line:
                    alert = [alert_line
                             for alert_line in contract.categ_id.alert_line]
                    if trigger_date == alert[0].name:
                        contract.alert_no = str(alert[0].sequence)
                    elif trigger_date <= alert[1].name and trigger_date > alert[2].name:
                        contract.alert_no = str(alert[1].sequence)
                    elif trigger_date <= alert[2].name and trigger_date > alert[3].name:
                        contract.alert_no = str(alert[2].sequence)
                    elif trigger_date <= alert[3].name and trigger_date > alert[4].name:
                        contract.alert_no = str(alert[3].sequence)
                    elif trigger_date <= alert[4].name and trigger_date > alert[0].name:
                        contract.alert_no = str(alert[4].sequence)
                    else:
                        contract.alert_no = '0'

    @api.depends('alert_no')
    def _alert_color(self):
        alert_pool = self.env['alerts']
        for contract in self:
            if contract.categ_id.alert_line \
                    and alert_pool.search([('sequence', '=', contract.alert_no)]) or contract.categ_id \
                    and contract.categ_id.alert_line and alert_pool.search([('sequence', '=', contract.alert_no)]):
                contract.alert_color = alert_pool.browse(
                    alert_pool.search([(
                        'sequence', '=', contract.alert_no)])[0]).alert_color
            else:
                contract.alert_color = 'black'

    @api.depends('state')
    def _get_status(self):
        contract_state_pool = self.env['res.contract.state']
        for contract in self:
            if contract.state in ['query', 'cancelled', 'admin_query',
                                  'cot_cancelled']:
                contract.res_contract_state_id = False
                contract.probability = 0.00
            contract_state = contract_state_pool.search(
                [('state', '=', contract.state)]) or False

            contract.res_contract_state_id = contract_state

            contract.probability = contract_state and contract_state.read(['probability'])[0][
                'probability'] or 0.00

    def _callback_count(self):
        for contract in self:
            phonecall_ids = self.env['crm.phonecall'].search(
                [('contract_id', '=', contract.id),
                 ('date', '>=', time.strftime('%Y-%m-%d %H:%M:%S')),
                 ('state', '!=', 'cancel')],
            )
            contract.write(
                {'callback_no': len(phonecall_ids)},
            )
        return True

    @api.model
    def _default_admin_user(self):
        admin_user_group_ids = self.env['res.groups'].search(
            [('name', '=', 'Contract / Admin Team')])
        for group in admin_user_group_ids:
            for group_user in group.users:
                user_id = group_user.id
                break
        return user_id.id

    def _calculate_commission_to_pay(self):
        reconcile_total = 0.0
        for line in self:
            line.commission_to_pay = 0.0
            if line.broker_reconcile_ids:
                for rec_obj in line.broker_reconcile_ids:
                    reconcile_total += rec_obj.comm_amount
            # res[line.id] = line.full_commission + reconcile_total
            line.commission_to_pay = line.broker_commission - \
                line.commission_first_payment - reconcile_total

    @api.depends('external_broker_reconcile_ids', 'broker_commission_first_payment')
    def _ext_calculate_commission_to_pay(self):
        reconcile_total = 0.0
        print("----------------")
        for line in self:
            line.ext_commission_to_pay = 0.0
            if line.external_broker_reconcile_ids:
                for rec_obj in line.external_broker_reconcile_ids:
                    reconcile_total += rec_obj.comm_amount
            if line.broker_commission_first_payment:
                line.ext_commission_to_pay = line.external_broker_commission - \
                    line.broker_commission_first_payment - reconcile_total
                # res[line.id] = line.external_full_commission - reconcile_total - line.broker_commission_first_payment
                # print "---external broker commission::>>>>", line.external_broker_commission
                # print "---broker_comission first pay in if condition::>>>>", line.broker_commission_first_payment
                # print "---unadjusted commission::>>>>", line.external_full_commission
                # print "---com amount reconcile total::>>>>", reconcile_total
                # print "res line id in if ::>>>>",res[line.id]
            else:
                # res[line.id] = line.external_full_commission - reconcile_total
                print("==============================",
                      line.external_broker_commission - reconcile_total)
                line.ext_commission_to_pay = line.external_broker_commission - reconcile_total

    @api.depends('year_duration', 'commission_payment_quant')
    def _calculate_broker_commission(self):
        for line in self:
            line.calculate_broker_commission = 0.0
            broker_split = \
                (line.default_section_id and
                 float(line.default_section_id.broker_split) / 100) or 1
            upfront_payment = \
                (line.default_section_id and
                 float(line.default_section_id.upfront_payment) / 100) or 1
            if line.year_duration:
                if line.commission_payment_quant == 'monthly':
                    line.calculate_broker_commission = \
                        ((line.broker_uplift * line.usage *
                          int(line.year_duration)) / 100) * broker_split
                elif line.commission_payment_quant == 'annually':
                    line.calculate_broker_commission = \
                        (line.broker_uplift * line.usage *
                         int(line.year_duration)) / 100 * (broker_split *
                                                           upfront_payment)
                else:
                    line.calculate_broker_commission = \
                        ((line.broker_uplift * line.usage *
                          int(line.year_duration)) / 100) * \
                        (broker_split * upfront_payment *
                         (line.commission_percentage / 100))

    @api.depends('year_duration', 'commission_payment_quant')
    def _calculate_external_broker_commission(self):
        res = {}
        comm_pool = self.env['contract.commission.confi']
        for line in self:
            res[line.id] = 0.0
            broker_split = \
                (line.default_section_id and
                 float(line.default_section_id.broker_split) / 100) or 1
            upfront_payment = \
                (line.default_section_id and
                 float(line.default_section_id.upfront_payment) / 100) or 1

            commi_year = comm_pool.search(
                [('year_duration', '=', line.year_duration),
                 ('supplier_id', '=', line.supplier_id.id),
                 ('external_broker', '=', True), ])

            supplier_contract_commission = commi_year and commi_year[0].percentage
            if isinstance(supplier_contract_commission, list):
                if not supplier_contract_commission:
                    supplier_contract_commission = 0.0

            if line.year_duration:
                if line.broker_commission_payment_quant == 'monthly':
                    line.calculate_external_broker_commission = \
                        ((line.broker_uplift * line.usage *
                          int(line.year_duration)) / 100) * broker_split
                elif line.broker_commission_payment_quant == 'annually':
                    line.calculate_external_broker_commission = \
                        (line.broker_uplift * line.usage *
                         int(line.year_duration)) / 100 * (broker_split *
                                                           upfront_payment)
                elif line.broker_commission_payment_quant == 'upfront':
                    line.calculate_external_broker_commission = \
                        line.usage * line.broker_uplift * int(line.year_duration) \
                        * (upfront_payment * 100) * (broker_split * 100) * supplier_contract_commission / pow(10, 8)
                else:
                    line.calculate_external_broker_commission = \
                        ((line.broker_uplift * line.usage *
                          int(line.year_duration)) / 100) * \
                        (broker_split * (line.broker_commission_percentage / 100))
        return res

    @api.depends('commission_reconcile_ids', 'paid_annually')
    def _commission_amount_diff_total(self):
        reconcile_total = 0.0
        supp_confi_obj = self.env['supplier.commission.confi']
        for line in self:

            supp_confi_ids = supp_confi_obj.search(
                [('year_duration', '=', line.year_duration),
                 ('supplier_id', '=', line.supplier_id.id)])
            supp_conf_browse = supp_confi_ids and \
                supp_confi_ids[0] or False
            if line.commission_reconcile_ids:
                for rec_obj in line.commission_reconcile_ids:
                    reconcile_total += rec_obj.com_amount
            if line.paid_annually:
                line.commission_amount_total = (
                    line.broker_commission - reconcile_total)
            else:
                tot = (line.broker_commission *
                       (supp_conf_browse and supp_conf_browse.percentage /
                        100 or 1) - reconcile_total)
                line.commission_amount_total = tot

    @api.depends('commission_reconcile_ids')
    def _get_total_amount_paid(self):
        total_amount_paid = 0.0
        for line in self:
            if line.commission_reconcile_ids:
                for rec_obj in line.commission_reconcile_ids:
                    total_amount_paid += rec_obj.com_amount
            line.total_amount_paid = total_amount_paid

    @api.depends('broker_reconcile_ids')
    def _brokercommission_amount_diff_total(self):
        reconcile_total = 0.0
        for line in self:
            if line.broker_reconcile_ids:
                for rec_obj in line.broker_reconcile_ids:
                    reconcile_total += rec_obj.comm_amount
            line.brokercommission_amount_total = reconcile_total

    @api.depends('commission_first_payment')
    def _calculate_full_commission_total(self):
        for line in self:
            line.full_commission = line.commission_first_payment

            #
            # def _compute_meter_data(self):
            #     for rec in self:
            #         orders = self.env['meter.data.line'].search([('contract_id', '=', rec.id)])
            #         rec.update({"meter_data" : len(orders.ids)})
            # rec.meter_data = len(orders)

    @api.depends('broker_commission_first_payment')
    def _calculate_ext_full_commission_total(self):
        for line in self:
            line.external_full_commission = line.broker_commission_first_payment

    def action_update_commission_data(self):
        comm_pool = self.env['contract.commission.confi']
        supp_confi_obj = self.env['supplier.commission.confi']
        for this_obj in self:
            tot = 0.0

            broker_split = \
                (this_obj.default_section_id and
                 float(this_obj.default_section_id.broker_split) / 100) or 1
            upfront_payment = \
                (this_obj.default_section_id and
                 float(this_obj.default_section_id.upfront_payment) / 100) or 1
            if this_obj.year_duration:
                commi_year = comm_pool.search(
                    [('year_duration', '=', this_obj.year_duration),
                     ('supplier_id', '=', this_obj.supplier_id.id),
                     ('external_broker', '=', False), ])
                if this_obj.commission_payment_quant == 'monthly':
                    tot = (this_obj.broker_uplift * this_obj.usage *
                           int(this_obj.year_duration)) / 100 * broker_split
                elif this_obj.commission_payment_quant == 'annually':
                    tot = (this_obj.usage * this_obj.broker_uplift *
                           int(this_obj.year_duration) / 100) * \
                          (broker_split * upfront_payment)
                    print('---print tot ::::>>>>>', tot)
                else:
                    tot = (this_obj.broker_uplift * this_obj.usage *
                           int(this_obj.year_duration)) / 100 * \
                        broker_split * this_obj.commission_percentage / 100
                reconcile_total = 0.0
                supp_rec_total = 0.0
                if this_obj.broker_reconcile_ids:
                    for rec_obj in this_obj.broker_reconcile_ids:
                        reconcile_total += rec_obj.comm_amount
                        print('---print reconcile total:::>>>>', reconcile_total)

                supp_confi_ids = supp_confi_obj.search(
                    [('year_duration', '=', this_obj.year_duration),
                     ('supplier_id', '=', this_obj.supplier_id.id)])
                supp_conf_browse = supp_confi_ids and supp_confi_ids[
                    0] or False

                if this_obj.commission_reconcile_ids:
                    for supp_rec_obj in this_obj.commission_reconcile_ids:
                        supp_rec_total += supp_rec_obj.com_amount
                if this_obj.paid_annually:
                    supp_rec_total_due = (
                        this_obj.broker_commission - supp_rec_total)
                else:
                    supp_rec_total_due = \
                        (this_obj.broker_commission *
                         (supp_conf_browse and
                          supp_conf_browse.percentage / 100 or 1) -
                         supp_rec_total)

                if this_obj.commission_reconcile_ids:
                    for supp_rec_obj in this_obj.commission_reconcile_ids:
                        supp_rec_obj.write(
                            {'comm_deducted_amount':
                             supp_rec_total_due - supp_rec_obj.com_amount})
                if commi_year:
                    com_obj = commi_year[0]
                    this_obj.write({
                        'dummy_commi_year_id': com_obj and com_obj.id or False,
                        'commi_year_id': com_obj and com_obj.id or False,
                        'dummy_commission_percentage': com_obj and com_obj.percentage or 0.0,
                        'commission_percentage': com_obj and com_obj.percentage or 0.0,
                        'calculate_broker_commission': tot,
                        'full_commission': this_obj.commission_first_payment,
                        'commission_amount_total': supp_rec_total_due,
                        'brokercommission_amount_total':
                            reconcile_total,
                        'commission_to_pay': tot + reconcile_total
                    })
        return True

    def action_update_broker_commission_data(self):
        comm_pool = self.env['contract.commission.confi']
        supp_confi_obj = self.env['supplier.commission.confi']

        for this_obj in self:
            tot = 0.0
            comm_pool = self.env['contract.commission.confi']
            if this_obj.default_section_id and this_obj.default_section_id.external_broker:
                ex_reconcile_total = 0.0
                if this_obj.external_broker_reconcile_ids:
                    for exrec_obj in this_obj.broker_reconcile_ids:
                        ex_reconcile_total += exrec_obj.comm_amount

                broker_split = \
                    (this_obj.default_section_id and
                     float(
                         this_obj.default_section_id.broker_split) / 100) or 1
                print("------broker split::>>>>>"), broker_split
                upfront_payment = \
                    (this_obj.default_section_id and
                     float(
                         this_obj.default_section_id.upfront_payment) / 100) or 1
                print("---------upfront payment::>>>>>", upfront_payment)
                commi_year = comm_pool.search(
                    [('year_duration', '=', this_obj.year_duration),
                     ('supplier_id', '=', this_obj.supplier_id.id),
                     ('external_broker', '=', True), ])

                supplier_contract_commission = commi_year and commi_year[
                    0].percentage
                print("----supplier commission contract::>>>>>>",
                      supplier_contract_commission)
                if this_obj.year_duration:
                    commi_year = comm_pool.search(
                        [('year_duration', '=', this_obj.year_duration),
                         ('supplier_id', '=', this_obj.supplier_id.id),
                         ('external_broker', '=',
                          this_obj.default_section_id.external_broker)])
                    if this_obj.broker_commission_payment_quant == 'monthly':
                        tot = (this_obj.broker_uplift * this_obj.usage *
                               int(
                                   this_obj.year_duration)) / 100 * broker_split
                    elif this_obj.broker_commission_payment_quant == 'annually':
                        tot = (this_obj.usage * this_obj.broker_uplift * int(
                            this_obj.year_duration) / 100) * (
                            broker_split * upfront_payment)
                        print("----print tot::>>>>>", tot)
                    elif this_obj.broker_commission_payment_quant == 'upfront':
                        tot = \
                            this_obj.usage * this_obj.broker_uplift * int(
                                this_obj.year_duration) \
                            * (upfront_payment * 100) * (
                                broker_split * 100) * supplier_contract_commission / pow(
                                10, 8)

                    else:
                        tot = (this_obj.broker_uplift * this_obj.usage *
                               int(this_obj.year_duration)) / 100 * \
                            broker_split * (
                            this_obj.broker_commission_percentage) / 100

                    if commi_year:
                        com_obj = commi_year[0]

                        this_obj.write({
                            'broker_commi_year_id': com_obj and com_obj.id or False,
                            'broker_commission_percentage': com_obj and com_obj.percentage or 0.0,
                            'calculate_external_broker_commission': tot,
                            # 'external_full_commission': tot,
                            'external_full_commission': this_obj.broker_commission_first_payment,
                            'ext_brokercommission_amount_total':
                                ex_reconcile_total,
                            'commission_to_pay': tot + ex_reconcile_total

                        })
        return True

    @api.onchange('contract_type_id')
    def onchange_contract_type_id(self):
        if not self.contract_type_id:
            self.acquisition_bool = False
        contact_name = self.contract_type_id
        if contact_name.name == 'Acquisition':
            self.acquisition_bool = True
        else:
            self.acquisition_bool = False

    def act_docusign_pending(self):
        # print "-====-===-=-="
        for this_obj in self:
            this_obj.write({'state': 'docusign_pending',
                            'last_state': 'docusign_pending'})
        return True

    def action_confirmed(self):
        for record in self:
            record.write({'state': 'confirmed',
                          'last_state': 'confirmed',
                          'admin_user_id': self.env.uid,
                          'date_admin_confirm': time.strftime('%Y-%m-%d')})
        return True

    def action_accepted(self):
        for this_obj in self:
            if not this_obj.supplier_ref:
                raise ValidationError(_('Incomplete Data!, You must enter \
                Supplier Ref before this contract can be accepted.'))
            this_obj.write({'state': 'accepted',
                            'last_state': 'accepted'})
        return True

    def action_complete(self):
        for record in self:
            res = {'livenocis': datetime.now().strftime("%Y%m%d %H%M%S"),
                   'state': 'complete', 'last_state': 'complete'}
            if record.default_section_id.external_broker:
                res.update(
                    {'commission_date': datetime.now().strftime("%Y%m%d %H%M%S")})
            record.write(res)
        return True

    def action_update_external_adjustments(self):
        for this_obj in self:
            for ex_br in this_obj.external_broker_reconcile_ids:
                ex_br.write({'is_external_broker': True})
        return True

    def action_cot_cancel(self):
        for this_obj in self:
            search_renew_id = self.search(
                [('renew_id', '=', this_obj.id)])
            if search_renew_id:
                search_renew_id.write({'superseded': False})
                search_renew_id.cron_call()
        self.write({'state': 'cot_cancelled',
                    'last_state': 'cot_cancelled'})
        return True

    def action_cancel(self):
        for this_obj in self:
            search_renew_id = self.search(
                [('renew_id', '=', this_obj.id)])
            if search_renew_id:
                search_renew_id.write(
                    {'superseded': False,
                     'check_renew': False},
                )
                search_renew_id.cron_call()
            docusign_email_id = self.env['docusign.document'].search(
                [('contract_id', '=', this_obj and this_obj.id or
                  False)])
            if docusign_email_id:
                docusign_email_id.write(
                    {'state': 'admin_cancel'})
        self.write({'state': 'cancelled',
                    'last_state': 'cancelled',
                    'query_code_id': False})
        return True

    @api.onchange('use_parent_address')
    def onchange_company_addr(self):
        if self.use_parent_address and self.partner_id:
            partner = self.partner_id
            self.street = partner.street or False
            self.street2 = partner.street2 or False
            self.city = partner.city or False
            self.zip = partner.zip or False
            self.state_id = partner.state_id and partner.state_id.id or False
            self.country_id = partner.country_id and partner.country_id.id or \
                False
        else:
            self.street = False
            self.street2 = False
            self.city = False
            self.zip = False
            self.state_id = False
            self.country_id = False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            partner = self.partner_id
            self.address_id = partner.child_ids and \
                partner.child_ids[0].id or False
        else:
            self.address_id = False

    @api.onchange('start_date')
    def onchange_date(self):
        if not self.start_date:
            self.loa_expiry = False

    def copy(self, default=None):
        default = {}
        self_obj = self
        new_start_date = (datetime.strptime(str(self_obj.end_date), '%Y-%m-%d') +
                          relativedelta(days=1))
        new_end_date = (
            datetime.strptime(str(self_obj.end_date),
                              '%Y-%m-%d') + relativedelta(
                days=0, years=int(self_obj.year_duration)))
        default_sale_type = self.env['contract.account'].search(
            [('name', '=', 'R')])
        default.update({
            'user_id': self.env.uid,
            'superseded': False,
            'start_date': new_start_date,
            'end_date': new_end_date,
            'confirmation_date': False,
            'commission_date': self_obj.default_section_id.external_broker and False or new_start_date,
            'loa_expiry': False,
            'cot_date': False,
            'state': 'draft',
            'partner_id': self_obj.partner_id.id,
            'supplier_id': self_obj.supplier_id.id,
            'previous_supplier_id':
                self_obj.supplier_id and self_obj.supplier_id.id,
            'contract_name':
                self.env['ir.sequence'].search([('name', '=', 'Contract')]),
            'sale_name': self.env['ir.sequence'].search([('name', '=', 'Sale Order')]),
                # self.env['ir.sequence'].sudo().get('res.contract'),
            'supplier_ref': '',
            'confirmation_medium': '',
            'admin_user_id': False,
            'admin_pro_user_id': False,
            'contract_account_id': default_sale_type and
                                   default_sale_type.id or False,
            'meter_data_id': False,
            'uplift_value': 0.00,
            'broker_uplift': 0.00,
            'usage': 0.00,
            'payment_type_id': self_obj.payment_type_id and self_obj.payment_type_id.id or False,
            'dd_collection_date': self_obj.dd_collection_date,
            'presale_termination_issued': False,
            'proof_of_usage': False,
            'pricing_type': False,
            'alert': False,
            'call_back_list': False,
            'rec_color': '',
            'alert_no': '0',
            'days_to_expiry': 0,
            'days_to_loa_expiry': '',
            'export_flag': False,
            'export_date': False,
            'export_flag_2': False,
            'export_date_2': False,
            'export_flag_3': False,
            'export_date_3': False,
            'export_flag_4': False,
            'export_date_4': False,
        })
        res_id = super(Contract, self).copy(
            default)
        if self_obj.meter_data_id:
            for data_line in self_obj.meter_data_id:
                print('--print meter data id ::>>>>', self.meter_data_id)
                data_line.copy(
                    default={'utility_type': self_obj.utility_type,
                             'contract_id': res_id.id},
                )
        return res_id

    @api.onchange('contract_terminated')
    def onchange_contract_terminated(self):
        if not self.contract_terminated:
            self.date_terminate = False
        self.date_terminate = time.strftime('%Y-%m-%d')

    @api.onchange('contract_audited')
    def onchange_contract_audited(self):
        if self.contract_audited:
            self.date_audit = time.strftime('%Y-%m-%d')
            self.date_audited_dummy = time.strftime('%Y-%m-%d')
        else:
            self.date_audit = False
            self.date_audited_dummy = False

    @api.onchange('presale_termination_issued')
    def onchange_presale_termination_issued(self):
        if self.presale_termination_issued:
            self.date_terminate_psti = time.strftime('%Y-%m-%d')
        else:
            self.date_terminate_psti = False

    # @api.onchange('contract_terminated')
    # def onchange_contract_termiated(self):
    #     if self.contract_terminated:
    #         self.date_terminate = time.strftime('%Y-%m-%d')
    #     else:
    #         self.date_terminate = False
    #

    @api.onchange('payment_type_id')
    def onchange_payment_type_id(self):
        res = {'payment_type_bool': False}
        if not self.payment_type_id:
            return {'value': res}
        if self.payment_type_id.requires_day:
            return {'value': {'payment_type_bool': True}}
        else:
            return {'value': res}

    def check_email_send(self, self_obj, template):
        check_send = True
        if self_obj.contract_send_mail_history_line:
            for history_line in self_obj.contract_send_mail_history_line:
                if history_line.state_to == self_obj.state:
                    check_send = False
        return check_send

    def send_email_for_status_change(self):
        context = dict(self._context or {})
        for self_obj in self:
            send_contract_email_ids = \
                self.env['send.contract.email'].search(
                    [('state', '=', self_obj.state),
                     ('supplier_line.partner_id', '=',
                      self_obj.supplier_id.id)])
            if send_contract_email_ids:
                res_supplier_template_ids = \
                    self.env['res.supplier.template'].search(
                        [('send_contract_email_id', '=',
                          send_contract_email_ids[0]),
                         ('partner_id', '=',
                          self_obj.supplier_id.id)])
                if res_supplier_template_ids:
                    res_supplier_template_browse = \
                        self.env['res.supplier.template'].browse(
                            res_supplier_template_ids.ids[0],
                        )
                    for template in res_supplier_template_browse.template_line:
                        check_send = self.check_email_send(
                            self_obj, template)
                        context.update(
                            {'attach_to_con': self_obj.attach_to_con})
                        if check_send:
                            self.env['email.template'].with_context(
                                context).send_mail(
                                template.template_id.id,
                                self_obj.id)
                        elif not template.once_check:
                            self.env['email.template'].send_mail(
                                template.template_id.id,
                                self_obj.id)
        return True

    def update_supplier_reconcile(self, current_id, vals):
        if vals.get('commission_reconcile_ids', False) or vals.get(
                'broker_commission', False):
            con_com_reco_obj = self.env['contract.commission.reconcile']
            previoue_data = 0.0
            remaining = 0.0
            for com_line in current_id.commission_reconcile_ids:
                first_line = current_id.commission_reconcile_ids[0]
                if com_line.id == first_line.id:
                    remaining = current_id.broker_commission - com_line.com_amount or 0.0
                    com_line.write({'comm_deducted_amount': remaining})
                    previoue_data = remaining
                else:
                    remaining = previoue_data - com_line.com_amount
                    com_line.write({'comm_deducted_amount': remaining or 0.0})
                    previoue_data = remaining

    @api.onchange('sale_name')
    def onchange_sale_name(self):
        if self.sale_name == '' or False:
            self.sale_boolean = True
        else:
            self.sale_boolean = False

    @api.model
    def default_get(self, fields):
        res = super(Contract, self).default_get(fields)
        if self.env.context.get('sale_menu', False):
            res.update({
                'so_boolean': True,
                'order_type': 'so',
                'sale_user_id': self.env.uid,
                'salesman_id': self.env.uid,
            })
        if self.env.context.get('contract_menu', False):
            res.update({
                'co_boolean': True,
                'order_type': 'co',
            })

        return res

    @api.model
    def create(self, vals):
        categ_id = False
        seq = self.env['ir.sequence'].search([('name', '=', 'Contract')])
        seq = seq.next_by_id() or '/'
        vals['sale_boolean'] = False
        vals['co_boolean'] = True
        vals['contract_name'] = seq
        print("================-----printed sequeence:>>>>>", seq)

        if vals.get('sale_end_date'):
            print('---print start date ::>>>>', vals.get('sale_start_date'))
            print('---print sale end _date', vals.get('sale_end_date'))
            sale_end_date = vals.get('sale_end_date')
            expiry_date = (datetime.strptime(str(sale_end_date),
                                             '%Y-%m-%d') - datetime.now()).days
            print('expiry date printed create method ::>>>>', expiry_date)
            vals['sale_days_to_expiry'] = expiry_date
        print('----va;s printed ::::<<<<>>>>>', vals)
        if vals.get('categ_id', False) or vals.get('usage', False):
            category_obj = self.env['product.category']
            categ_id = category_obj.browse(vals.get('categ_id'))
            vals.update(
                {'edit_broker_commission': categ_id.edit_broker_commission,
                 'edit_internal_commission': categ_id.edit_internal_commission})
        if 'dummy_commi_year_id' in vals:
            vals.update({'commi_year_id': vals['dummy_commi_year_id']})
        if 'dummy_commission_percentage' in vals:
            vals.update({'commission_percentage':
                         vals['dummy_commission_percentage']})
        if 'dummy_broker_commi_year_id' in vals:
            vals.update(
                {'broker_commi_year_id': vals['dummy_broker_commi_year_id']})
        if 'dummy_broker_commission_percentage' in vals:
            vals.update({'broker_commission_percentage':
                         vals['dummy_broker_commission_percentage']})
        if 'export_date_dummy' in vals:
            vals.update({'export_date': vals['export_date_dummy']})
        if 'export_date_2_dummy' in vals:
            vals.update({'export_date_2': vals['export_date_2_dummy']})
        if 'export_date_3_dummy' in vals:
            vals.update({'export_date_3': vals['export_date_3_dummy']})
        if 'export_date_4_dummy' in vals:
            vals.update({'export_date_4': vals['export_date_4_dummy']})
        if not vals.get('edit_internal_commission',
                        False) and categ_id and not categ_id.edit_internal_commission:
            usage = vals.get('usage', False) or 0.0
            broker_uplift = vals.get('broker_uplift', False) or 0.0
            year_duration = vals.get('year_duration', False) or 0.0
            vals.update({'broker_commission': (
                usage * broker_uplift / 100 * float(year_duration))})
        if not vals.get('edit_broker_commission',
                        False) and categ_id and not categ_id.edit_broker_commission:
            crm_case_section_id = False
            broker_split = 0.0
            if vals.get('default_section_id', False):
                crm_case_obj = self.env['crm.team']
                crm_case_section_id = crm_case_obj.browse(
                    vals.get('default_section_id'))
                broker_split = crm_case_section_id and crm_case_section_id.broker_split or 0.0
            vals.update({'external_broker_commission': (vals.get(
                'broker_commission', False) or 0.0 * broker_split) / 100})
        res = super(Contract, self).create(vals)
        current_id = res
        if vals.get('commission_reconcile_ids', False) or vals.get(
                'broker_commission', False):
            self.update_supplier_reconcile(current_id, vals)
        return res

    def write(self, vals):
        # print ("------valss:::>>>>", vals)
        categ_id = False
        current_id = self
        if vals.get('order_type') == 'co':
            seq = self.env['ir.sequence'].search([('name', '=', 'Contract')])
            seq = seq.next_by_id() or '/'
            vals['contract_name'] = seq
            print("================-----printed sequeence:>>>>>", seq)
        # if vals.get('sale_end_date'):
        #     expiry_date = (datetime.strptime(str(self.sale_end_date), '%Y-%m-%d') - datetime.now()).days
        #     print ('expiry date printed write method::>>>>', expiry_date)
        #     vals['sale_days_to_expiry'] = expiry_date
        if vals.get('categ_id', False) or vals.get('usage', current_id.usage):
            category_obj = self.env['product.category']
            categ_id = category_obj.browse(
                vals.get('categ_id', current_id.categ_id.id))
            vals.update(
                {'edit_broker_commission': categ_id.edit_broker_commission,
                 'edit_internal_commission': categ_id.edit_internal_commission})
        if 'dummy_commi_year_id' in vals:
            vals.update({'commi_year_id': vals['dummy_commi_year_id']})
        if 'dummy_commission_percentage' in vals:
            vals.update({'commission_percentage':
                         vals['dummy_commission_percentage']})
        if 'dummy_broker_commi_year_id' in vals:
            vals.update(
                {'broker_commi_year_id': vals['dummy_broker_commi_year_id']})
        if 'dummy_broker_commission_percentage' in vals:
            vals.update({'broker_commission_percentage':
                         vals['dummy_broker_commission_percentage']})
        # if 'date_audited_dummy' in vals:
        #     vals.update({'date_audited': vals['date_audited_dummy']})
        if 'export_date_dummy' in vals:
            vals.update({'export_date': vals['export_date_dummy']})
        if 'export_date_2_dummy' in vals:
            vals.update({'export_date_2': vals['export_date_2_dummy']})
        if 'export_date_3_dummy' in vals:
            vals.update({'export_date_3': vals['export_date_3_dummy']})
        if 'export_date_4_dummy' in vals:
            vals.update({'export_date_4': vals['export_date_4_dummy']})
        if 'state' in vals:
            for self_browse in self:
                from_state = self_browse.state or False
                to_state = vals['state']
                res_history = {
                    'name': 'Status Change',
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'state_from': from_state,
                    'state_to': to_state,
                    'contract_id': self_browse and self_browse.id or False,
                }
        if not vals.get('edit_internal_commission',
                        False) and categ_id and not categ_id.edit_internal_commission:
            year_duration = float(
                vals.get('year_duration', float(current_id.year_duration)))
            vals.update({'broker_commission': (
                vals.get('usage', current_id.usage) * vals.get(
                    'broker_uplift',
                    current_id.broker_uplift) / 100 * year_duration)})
        if not vals.get('edit_broker_commission',
                        False) and categ_id and not categ_id.edit_broker_commission:
            crm_case_section_id = False
            broker_split = False
            if vals.get('default_section_id', False):
                crm_case_obj = self.env['crm.team']
                crm_case_section_id = crm_case_obj.browse(
                    vals.get('default_section_id'))
                broker_split = crm_case_section_id and crm_case_section_id.broker_split or 0.0
            else:
                broker_split = current_id.default_section_id.broker_split
            vals.update({'external_broker_commission': (vals.get(
                'broker_commission',
                current_id.broker_commission) * broker_split) / 100})
        res = super(Contract, self).write(vals)
        if vals.get('commission_reconcile_ids', False) or vals.get(
                'broker_commission', False):
            self.update_supplier_reconcile(current_id, vals)

        if vals and vals.get('state', False):
            self.send_email_for_status_change()
            self.env['contract.send.email.history'].create(res_history)
        # if vals and vals.get('user_id', False) and vals['user_id']:
        #     for contract in self:
        #         if contract.so_id and not contract.so_id.user_id.id == \
        #                                   vals['user_id']:
        #             contract.so_id.write(
        #                 {'user_id': vals['user_id']},
        #             )

        return res

    @api.model
    def x_search(self, args, offset=0, limit=None, order=None, count=False):
        import sys
        if 'loa_lead_time_menu_click' in self._context:
            # print ('---search method:::>>', self._context)
            if self._context.get('loa_lead_time_menu_click', False):
                # sys.setrecursionlimit(5000)
                # ss
                print('---print time strf time ::>>',
                      time.strftime('%Y-%m-%d'))
                # 2/0
                con_search = self.env['res.contract'].search([('renew_id', '=', False),
                                                              ('loa_expiry', '>=', time.strftime('%Y-%m-%d'))])
                # con_search = self.search(
                #     [('renew_id', '=', False),
                #      ('loa_expiry', '>=', time.strftime('%Y-%m-%d'))])
                print('---printed length of con search :::>>>>', len(con_search))
                for contract in con_search:
                    trigger_date = \
                        (datetime.today() + relativedelta(days=contract.loa_lead_time)
                         ).strftime('%Y-%m-%d')
                    if contract.loa_expiry > trigger_date:
                        print('--print contract id ::>>>>', contract)
                        con_search.remove(contract.id)
                args = [('id', 'in', con_search)]
        else:
            return super(Contract, self).search(args=args, offset=0, limit=None, order=None, count=False)
        return super(Contract, self).search(args=args, offset=0, limit=None,
                                            order=None, count=False)

    def action_send_docusign_doc(self):

        return {'name': 'Docusign Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'docusign.mail.wiz',
                # 'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                # 'context': {'default_contract_id': rec.id,}
                }

    def action_send_doc_email(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference(
                'dernetz', 'loa_crm_contract.odt')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        print('---print template id ::>>>', template_id)
        print('--print compose form id :::>>>', compose_form_id)
        ctx = {
            'default_model': 'res.contract',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            # 'mark_so_as_sent': True,
            # 'custom_layout': "mail.mail_notification_paynow",
            # 'proforma': self.env.context.get('proforma', False),
            # 'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            # 'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def action_udicore_docusign(self):

        return {'name': 'UDcore Docusign',
                'type': 'ir.actions.act_window',
                'res_model': 'send.udcore.docusign',
                # 'view_type': 'form',
                'view_mode': 'form',
                'target': 'new', }

    state = fields.Selection([
        ('draft', 'Draft'),
        ('doc_pending', 'Pending(Admin)'),
        ('docusign_pending', 'Delivered(Docusign)'),
        ('sale_agreed', 'Sale Confirmed'),
        ('confirmed', 'Admin Confirmed'),
        ('accepted', 'Supplier Accepted'),
        ('live', 'LIVE'),
        ('complete', 'LiveNocis'),
        ('livenocis_scanned', 'LiveNOCIS Scanned'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('query', 'Sales Query'),
        ('admin_query', 'Admin Query'),
        ('cot_cancelled', 'COT Cancelled'),
        ('cancelled', 'Cancelled')
    ], 'status', default='draft')

    last_state = fields.Selection([('draft', 'Draft'),
                                   ('doc_pending', 'Pending(Admin)'),
                                   ('docusign_pending', 'Delivered(Docusign)'),
                                   ('sale_agreed', 'Sale Agreed'),
                                   ('confirmed', 'Confirmed'),
                                   ('accepted', 'Accepted'),
                                   ('live', 'LIVE'),
                                   ('complete', 'Complete'),
                                   ('livenocis_scanned', 'LiveNOCIS Scanned'),
                                   ('payment_confirmed', 'Payment Confirmed'),
                                   ('cot_cancelled', 'COT Cancelled'),
                                   ('cancelled', 'Cancelled'),
                                   ('admin_query', 'Admin Query'),
                                   ('query', 'Sales Query')], string='Last State', default='draft')

    capacity = fields.Float(string="Capacity")
    other_price_1_dummy = fields.Char(string="Dummy Price", size=44)
    # docusign_recieved = fields.char(string='Docusign') #readonly=True

    name = fields.Char(string="Code")
    superseded = fields.Boolean(string="Superseded")
    # res_contract_state_id = fields.Many2one('res.contract.state',
    # compute = _get_status, string='Contract Status', store=True)
    # _get_status, method=True, type="many2one", store=True, string='Contract Status',
    # relation="res.contract.state", multi="probability"
    # probability = fields.Float(string='Percentage',
    # compute = _get_status)  # _get_status, string="Percentage", type="float",
    # method=True, store=True,  multi="probability"
    meter_read = fields.Integer(string='Meter Read')
    meter_read_date = fields.Date(string='Meter Read Date')

    days_to_expiry = fields.Integer(string="Days To Expiry")
    days_to_loa_expiry = fields.Char(string='Days To LOA Expiry', size=32)

    # note_button = fields.Char(String="Note")
    meter_data = fields.Integer(
        compute='_compute_meter_data', string="Meter Data")
    sale_meter_data = fields.Integer(
        compute='_compute_sale_meter_data', string="Meter Data")
    # note_button = fields.Char(String="Note")

    start_date = fields.Date(string="Start Date", )
    # default=lambda self: fields.Datetime.now()
    commission_date = fields.Datetime(string="Commission Date", )
    livenocis = fields.Datetime(string="LiveNOCIS Date")
    payment_confirmed_date = fields.Date(string="Payment Confirmed Date")
    year_duration = fields.Selection([('1', '1 years'),
                                      ('2', '2 Years'),
                                      ('3', '3 Years'),
                                      ('4', '4 Years'),
                                      ('5', '5 Years')], string='Duration')
    end_date = fields.Date(string="End Date")
    confirmation_date = fields.Date(string="Confirmation Date")
    # general_note = fields.One2many('partner_id', 'general_note', string="General Note")
    mpan_code = fields.Char(string='MPAN/MPR', size=64,
                            compute=_get_meter_data_line_code)
    mpan_code_first = fields.Char(string="Meter ID")
    # compute=_get_meter_data_line_code)
    #  mpan_code_first =fields.Char(string="Meter ID")
    mtc_code = fields.Char(string='MTC Code', size=3)
    uplift_id = fields.Many2one('res.uplift', string='Uplift Scale')
    alert = fields.Boolean(string="Alert", compute=_calc_alert,
                           store=True)  # _calc_alert, string='Alert',type='boolean', method=True, store=True
    date_finalized = fields.Datetime(stirng='Date Finalised')
    date_admin_confirm = fields.Date(String="Date Submitted")
    callback_no = fields.Integer('CallBack')
    # id_partner = fields.related('partner_id', 'id', type="integer",
    # string="Customer #", readonly=True)
    loa_expiry = fields.Date(string="LOA Expiry")
    qty = fields.Float(string='Qty')
    cot_date = fields.Date(string="COT Date")
    cancelled_date = fields.Date(string="Cancelled Date")

    uplift_value = fields.Float(string="UpLift Value")
    gas_usage = fields.Float(string='Gas Usage', readonly=True)
    gas_usage_charge = fields.Float(string='Gas Usage Charge', readonly=True)
    gas_standing = fields.Float(string='Gas Standing', readonly=True)
    company_registration_number = fields.Char(
        string='company registration number', size=32)
    charity_reg_no = fields.Char(string='Charity Reg. No.', size=32)
    sys_contract_id = fields.Integer(string='Contract ID')
    old_sys_id = fields.Integer(string='Sys Customer ID')
    paid_annually = fields.Boolean(string='Paid Annually ?')
    call_back_list = fields.Selection([('h', 'High'),
                                       ('l', 'Low'),
                                       ('ex', 'Expired')],
                                      string='Call Back List')
    broker_uplift = fields.Float(string="Internal UpLift")
    supplier_uplift = fields.Float(string="Supplier UpLift")
    broker_commission = fields.Float(string="Internal Commission")
    ad_hoc_commission = fields.Float(string="Ad-HOC Commission")
    external_broker_commission = fields.Float(sting="Broker Commission")
    supplier_commission = fields.Float(
        compute=_calulate_supplier_commission, sting="Supplier Commission", store=True)
    # meter_data_line = fields.One2many('meter.data.line', 'contract_id', string='Meter Data Line')
    payment_type_bool = fields.Boolean(string='Payment Type')
    usage_type_ration = fields.Integer(sting="User Type Ration", default=100)
    ldz_code = fields.Char(string='LDZ Code', size=4)

    categ_id = fields.Many2one("product.category", string="Category")
    sale_categ_id = fields.Many2one("product.category", string="Category")
    standing_charge = fields.Float(string='Standing Charge')
    primary_rate = fields.Float(string='Primary Rate')
    secondary_rate = fields.Float(string='Secondary Rate')
    tertiary_rate = fields.Float(string='Tertiary Rate')
    standing_charge_sell = fields.Float(string='Standing Charge')
    primary_rate_sell = fields.Float(string='Primary Rate')
    secondary_rate_sell = fields.Float(string='Secondary Rate')
    tertiary_rate_sell = fields.Float(string='Tertiary Rate')
    usage = fields.Integer(string="Usage")
    uom_id = fields.Many2one('product.uom', string='UoM')
    proof_of_usage = fields.Many2one('proof.of.usage', string="Proof Of Usage")
    pricing_type = fields.Many2one('pricing.type', string="Pricing Type")
    sale_pricing_type = fields.Many2one('pricing.type', string="Pricing Type")

    partner_id = fields.Many2one('res.partner', string='Partner', domain=[
                                 ('customer', '=', True)])
    sale_partner_id = fields.Many2one(
        'res.partner', string='Partner', domain=[('customer', '=', True)])
    des_partner_id = fields.Many2one(
        'res.partner', string='Designated Contact', domain=[('customer', '=', True)])
    address_id = fields.Many2one('res.partner', string='Correspondence')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[
                                  ('supplier', '=', True)])
    previous_supplier_id = fields.Many2one(
        'res.partner', 'Previous Supplier', domain=[('supplier', '=', True)])
    supplier_ref = fields.Char(string='Supplier Ref.')
    loa_lead_time = fields.Integer(string='LOA Lead Time')
    acquisition_bool = fields.Boolean(string='Acquisition')
    verbal_contract_id = fields.Many2one(
        'contract.verbal.open', 'Verbal Contract')
    branch_con_check = fields.Boolean(string='Include Verification')
    debit_with_current_supplier = fields.Boolean(
        string='Debt with current supplier')
    check_renew = fields.Boolean(string='Renew Check')

    previous_contract_end_date = fields.Date(
        string='Previous Contract End Date')
    # previous_sale_agent_id = fields.Many2one('res.users', string='Previous Sales Agent')
    previous_user_id = fields.Many2one('res.users', string='Previous Agents')
    # address = fields.Char(string="Address")
    street = fields.Char(related='partner_id.street')
    street2 = fields.Char(related='partner_id.street2')
    zip = fields.Char(related='partner_id.zip')
    city = fields.Char(related='partner_id.city')
    state_id = fields.Many2one(
        "res.country.state", string='State', related='partner_id.state_id')
    country_id = fields.Many2one(
        'res.country', string='Country', related='partner_id.country_id')

    supplier_for_docusign = fields.Selection([('Axis', 'Axis.'),
                                              ('Bristol Energy',
                                               'Bristol Energy.'),
                                              ('British Gas', 'British Gas.'),
                                              ('British Gas Lite',
                                               'British Gas Lite.'),
                                              ('Clear Business',
                                               'Clear Business.'),
                                              ('Brook Green', 'Brook Green.'),
                                              ('CNG', 'CNG.'),
                                              ('Crown', 'Crown.'),
                                              ('Corona Energy', 'Corona Energy.'),
                                              ('D-ENERGi', 'D-ENERGi.'),
                                              ('Dual Energy', 'Dual Energy.'),
                                              ('Ecotricity', 'Ecotricity.'),
                                              ('EDF', 'EDF.'),
                                              ('Dong', 'Dong.'),
                                              ('Engie', 'Engie.'),
                                              ('E-ON', 'E-ON.'),
                                              ('Extra Energy', 'Extra Energy.'),
                                              ('Gazprom', 'Gazprom.'),
                                              ('Haven', 'Haven.'),
                                              ('Hudson Energy', 'Hudson Energy.'),
                                              ('LoCO2', 'LoCO2.'),
                                              ('Npower', 'Npower.'),
                                              ('Opus', 'Opus.'),
                                              ('Opal', 'Opal.'),
                                              ('Scottish And Southern',
                                               'Scottish And Southern.'),
                                              ('Scottish Power',
                                               'Scottish Power.'),
                                              ('Simple Gas', 'Simple Gas.'),
                                              ('Total Energy', 'Total Energy.'),
                                              ('Total Gas And Power',
                                               'Total Gas And Power.'),
                                              ('United Gas And Power',
                                               'United Gas And Power.'),
                                              ('Utilita', 'Utilita.'),
                                              ('Yorkshire Gas And Power',
                                               'Yorkshire Gas And Power.'),
                                              ('Docusign not supported', 'Docusign not supported.'), ],
                                             string='UDcore Supplier Name')

    utility_type_gas_docusign = fields.Boolean(string="Utility Type Gas")
    utility_type_elec_docusign = fields.Boolean(string="Utility Type Elec")
    sse_billing_period = fields.Selection(
        [('Quarterly', 'Quarterly'), ('Monthly', 'Monthly')], string='SSE Billing Period')
    utility_type = fields.Selection([('ele', 'Electricity'),
                                     ('gas', 'GAS'),
                                     ('tel', 'Telecoms'), ('wat', '')], string='Utility Type')
    contract_account_id = fields.Many2one(
        'contract.account', string="Sales Type")
    contract_type_id = fields.Many2one('contract.type', string="Contract Type")
    contract_subtype_id = fields.Many2one(
        'contract.subtype', string="Contract Subtype")
    payment_type_id = fields.Many2one('payment.type', string="Payment Type")
    dd_collection_date = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
                                           ('6', '6'), ('7', '7'), ('8',
                                                                    '8'), ('9', '9'), ('10', '10'),
                                           ('11', '11'), ('12', '12'), ('13',
                                                                        '13'), ('14', '14'),
                                           ('15', '15'), ('16', '16'), ('17',
                                                                        '17'), ('18', '18'),
                                           ('19', '19'), ('20', '20'), ('21',
                                                                        '21'), ('22', '22'),
                                           ('23', '23'), ('24', '24'), ('25',
                                                                        '25'), ('26', '26'),
                                           ('27', '27'), ('28', '28')], string='DD Collection Day')
    debt_with_current_supplier = fields.Boolean(
        string="Debt With Current Supplier")

    create_date = fields.Date('Create Date')
    sales_query_agent = fields.Many2one(
        'res.users', string='Sales Query Agent')
    sales_query_level = fields.Selection([('1', '1'), ('2', '2'), ('3', '3')],
                                         string="Sales Query Level")
    renew_id = fields.Many2one('res.contract', string="Renewed Contract")
    region_id = fields.Many2one('res.region', string='Region')
    profile_id = fields.Many2one('res.profile', string='Profile')
    company_id = fields.Many2one('res.company', string="Company")
    use_parent_address = fields.Boolean('Use Partner Address',
                                        help="Select this if you want to set company's \ address for this contract")
    user_id = fields.Many2one('res.users', string="Sales Agent")
    default_section_id = fields.Many2one('crm.team', string="Broker")
    section_id = fields.Many2one('crm.team', string="Broker")
    admin_user_id = fields.Many2one('res.users', string="Admin Agent")
    admin_pro_user_id = fields.Many2one('res.users', string="Processed By")
    sale_query_agent = fields.Many2one('res.users', string="Sales Query Agent")
    sale_query_level = fields.Selection([('1', '1'),
                                         ('2', '2'),
                                         ('3', '3')], string="Sales Query Level")
    agent_id = fields.Many2one('res.users', string="Agent ID")

    sale_confirmed_letter_sent = fields.Boolean(
        string="Sale Confirmed Letter Sent")
    sale_confirmed_date = fields.Datetime(string="Sale Confirmed Date")
    welcome_letter_sent = fields.Boolean(string="Welcome Letter Sent")
    welcome_letter_date = fields.Datetime(string="Welcome Letter Date")
    livenocis_date = fields.Datetime(string='LiveNOCIS Date')
    via_verbal = fields.Boolean(string="Verbal Confirmation?")
    via_written = fields.Boolean(string="Written Confirmation?")
    via_electronic = fields.Boolean(string="Electronic Confirmation?")
    smart_meter = fields.Boolean(string="Smart Meter")
    bei = fields.Boolean(string="Corporate")
    renew_check = fields.Boolean(string='Renew Check')
    query_code_id = fields.Many2one('query.code', string='Query Code')
    ebilling = fields.Boolean(string="E-Billing")

    verbal_text_id = fields.Char(string='Verbal Text')
    written_template_id = fields.Char(string='Written Template')
    electronic_template_id = fields.Char(string='Electronic Template')
    meter_surcharge = fields.Float(string='Meter Surcharge Â£')

    confirmation_medium = fields.Selection([('ver', 'Verbal'),
                                            ('wri', 'Written'),
                                            ('ele', 'Electronic')], string='Confirmation Medium')

    service_id = fields.Char(string="Service ID")
    split_contract = fields.Boolean(string="Split Contract")
    dataref = fields.Char(string='Data Reference', size=16)
    poor_credit = fields.Boolean(string="Poor Credit")

    presale_termination_issued = fields.Boolean(
        string="Pre-Sale Termination Issued")

    contract_terminated = fields.Boolean(string="Contract Terminated")

    contract_audited = fields.Boolean(string="Internal Audit")
    date_audit = fields.Date(string="Internal Date Audit")
    date_audited_dummy = fields.Date(string='Internal Audit Date')

    clean_user_id = fields.Many2one('res.users', string="Cleansed By")
    clean_datetime = fields.Datetime(string="Cleansed On")

    export_flag = fields.Boolean(string="Export 1")
    export_date = fields.Datetime(string="Export 1 Date")
    export_date_dummy = fields.Datetime('Export 1 Date Dummy')

    export_flag_2 = fields.Boolean(string="Under 90 Export")
    export_date_2 = fields.Datetime(string="Under 90 Export Date")
    export_date_2_dummy = fields.Datetime('Under 90 Export Date Dummy')
    lost = fields.Boolean(String="Lost")

    export_flag_3 = fields.Boolean(string="Customer Service Export")
    export_date_3 = fields.Datetime(string="Customer Service Export Date")
    export_date_3_dummy = fields.Datetime(
        string='Customer Service Export Date Dummy')

    export_flag_4 = fields.Boolean(string="Export 4")
    export_date_4 = fields.Datetime(string="Export 4 Date")
    export_date_4_dummy = fields.Datetime(string='Export 4 Date Dummy')

    water_export = fields.Boolean('Water Export')
    water_export_date = fields.Datetime('Water Export Date')
    cot_ref = fields.Char(string="COT Reference")
    attach_to_con = fields.Boolean(string="Attach to contract record?")
    contract_send_mail_history_line = fields.One2many('contract.send.email.history', 'contract_id',
                                                      string='Send Mail History')

    note = fields.Char("Note")
    add = fields.Datetime("ADD DATE & TIME")

    note_admin_ids = fields.One2many("res.note", "admin_note_line_id")
    note_sales_ids = fields.One2many("res.note", "sales_note_line_id")
    date_terminate = fields.Date('Termination Date')
    date_terminate_psti = fields.Date(string='Termination Date')
    supplier_acceptance_code = fields.Char(
        string='Supplier Acceptance Code', size=256)
    supplier_acceptance_code_psti = fields.Char(
        string='Supplier Acceptance Code', size=256)
    alert_no = fields.Char(compute=_set_alert_no,
                           string="Alert No.",
                           store=True)  # _set_alert_no, type="char",
    # string='Alert No', size=10, method=True, store=True
    rec_color = fields.Char(string="Colour",
                            compute=_alert_color)  # _alert_color, string='Color', type='char', method=True

    check_accuracy = fields.Boolean(string="Accuracy Checked")
    commission_payment_quant = fields.Selection([('annually', 'Annually'),
                                                 ('monthly', 'Monthly')],
                                                string="Commission Payment Quant")
    commission_paid_bool = fields.Boolean(string="Commission Paid")
    date_finalised = fields.Datetime(string="Date Finalised")
    month_paid = fields.Date(string="Month Paid")
    commission_first_payment = fields.Float(String="Commission First Paid")

    commi_year_id = fields.Many2one(
        'contract.commission.confi', string="Commission Year")
    commission_percentage = fields.Float(string="Commission Percentage")

    general_note_contract_ids = fields.One2many(
        "general.note", "contract_id", string="General Note IDs")

    broker_reconcile_ids = fields.One2many(
        "broker.commission.reconcile", "broker_reconcile_line_id")
    contract_send_mail_history_line_ids = fields.One2many('contract.send.email.history', 'contract_id',
                                                          string='Send Mail History')

    total_amount_paid = fields.Float(
        string="Total Amount Paid:", compute=_get_total_amount_paid, store=True)

    commission_amount_total = fields.Float(string='Outstanding Supplier Amount', compute=_commission_amount_diff_total,
                                           store=True)  # _commission_amount_diff_total,
    # store={'res.contrac':(lambda self, cr, uid, ids, context=None:
    # ids, ['year_duration', 'paid_annually',
    #   'broker_commission',
    #  'commission_reconcile_ids'], 10), })

    broker_accuracy_checked = fields.Boolean(string="Broker Accuracy Checked")
    broker_commission_paid_bool = fields.Boolean(string="Commission Paid")
    broker_commission_payment_quant = fields.Selection([('annually', 'Annually'),
                                                        ('monthly', 'Monthly'),
                                                        ('upfront', 'UpFront')],
                                                       string="Commission Payment Quant")
    broker_date_finalised = fields.Datetime(string="Date Finalised")
    broker_commission_first_payment = fields.Float(
        string="Commission First Payment")

    broker_commi_year_id = fields.Many2one(
        'contract.commission.confi', string="Commission Year")
    broker_commission_percentage = fields.Float(string="Commission Percentage")
    dummy_commi_year_id = fields.Many2one(
        'contract.commission.confi', string='Commission Year')
    dummy_broker_commi_year_id = fields.Many2one(
        'contract.commission.confi', string='Commission Year')
    dummy_commission_percentage = fields.Float(string='Commission Percentage')
    dummy_broker_commission_percentage = fields.Float(
        string='Commission Percentage')
    calculate_broker_commission = fields.Float(compute=_calculate_broker_commission,
                                               string='Broker Commission Total', store=True
                                               )

    calculate_external_broker_commission = fields.Float(string="Broker Commission Total",
                                                        compute=_calculate_external_broker_commission, store=True)

    full_commission = fields.Float(string="Unadjusted Commission:", compute=_calculate_full_commission_total,
                                   store=True)
    brokercommission_amount_total = fields.Float(string="Total Adjustments:",
                                                 compute=_brokercommission_amount_diff_total, store=True)
    commission_to_pay = fields.Float(
        string="Commission To Pay:", compute=_calculate_commission_to_pay)
    ext_commission_to_pay = fields.Float(string="Commission To Pay:",
                                         compute=_ext_calculate_commission_to_pay, store=True)

    edit_internal_commission = fields.Boolean(
        string='Edit Internal Commission')  # ('categ_id', 'edit_internal_commission', store=True)
    edit_broker_commission = fields.Boolean(
        string='Edit Broker Commission')  # 'categ_id', 'edit_broker_commission', store=True)

    external_full_commission = fields.Float(string="Unadjusted Commission:",
                                            compute=_calculate_ext_full_commission_total)
    ext_brokercommission_amount_total = fields.Float(string="Total Adjustments:",
                                                     compute=_ext_brokercommission_amount_diff_total)
    # ext_brokercommission_to_pay = fields.Float(string="Commission To Pay:")

    commission_reconcile_ids = fields.One2many('contract.commission.reconcile', 'contract_id',
                                               stirng='Supplier Reconcile')

    # sale_order_id = fields.Many2one("sale.order", string="Sale order ID")
    # sale_order_line_id = fields.Many2one("sale.line", string="sale Order Line ID")
    meter_data_id = fields.Many2one("meter.data.line", string="Meter Data ID")
    sale_meter_data_id = fields.Many2one(
        "meter.data.line", string="Meter Data ID")

    broker_reconcile_ids = fields.One2many("broker.commission.reconcile", "internal_reconcile_line_id",
                                           string='Commission Payments/Adjustments')
    external_broker_reconcile_ids = fields.One2many('broker.commission.reconcile', 'external_reconcile_line_id',
                                                    string='Commission Payments/Adjustments')

    contract_name = fields.Char('Contract Name')

    rec_name = fields.Char('Rec Name', compute="_compute_rec_name")
    docusign_received = fields.Char('Docusign')
    docusign_sent_datetime = fields.Datetime('Docusign Sent')
    docusign_received_datetime = fields.Datetime('Docusign Recieved')

    # fields for Sale are as below ------------/|\--------------

    order_type = fields.Selection(
        [('so', 'Sale Order'), ('co', 'Contract Order')], string='Order Type')
    so_boolean = fields.Boolean("Sale Order")
    co_boolean = fields.Boolean("Contract Order")
    sale_name = fields.Char('Sale Name')
    # renew_so_id = fields.Char('Renew SO Id')
    sale_order_id = fields.Many2one('res.contract', 'Sale Order')
    renew_so_id = fields.Many2one('res.contract', 'Renew SO Id')
    sale_street = fields.Char('Sale Street')
    sale_state = fields.Selection([('draft', 'Draft'), ('contract', 'Contract'), (
        'cancel', 'Cancel'), ('sent', 'Sent')], string='State', default='draft')
    # customer_id = fields.Many2one('res.partner',string='Customer')
    designated_part_id = fields.Many2one(
        'res.partner', string='Designated Partner')
    date_order = fields.Datetime('Date')
    client_order_ref = fields.Char('Reference/Description')
    sale_user_id = fields.Many2one('res.users', string='Salesperson')
    sale_export_flag = fields.Boolean('Export Flag')
    sale_export_date = fields.Datetime('Export Date')
    sale_start_date = fields.Date('Start Date')
    sale_end_date = fields.Date('End Date')
    sale_days_to_expiry = fields.Integer(
        'Days to Expiry', compute='compute_expiry_date')
    sale_year_duration = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
                                          string='Duration')
    sale_contract_id = fields.Many2one("res.contract", "Contract")
    sale_uplift_value = fields.Float('Uplift Value')
    sale_supplier_uplift = fields.Float(
        'Supplier Uplift', compute="calculate_sale_supplier_uplift")
    sale_broker_uplift_value = fields.Float('Broker Uplift')
    sale_commission = fields.Float('Commission')
    sale_usage = fields.Integer('Usage')
    sale_supplier_id = fields.Many2one(
        'res.partner', string='Supplier', domain=[('supplier', '=', True)])
    sale_payment_type_id = fields.Many2one(
        'payment.type', string='Payment Type')
    sale_account_id = fields.Many2one('contract.account', string='Sale Type')
    sale_contract_type_id = fields.Many2one(
        'contract.type', string='Contract Type')
    sale_contract_subtype_id = fields.Many2one(
        'contract.subtype', string='Contract Subtype')
    sale_smart_meter = fields.Boolean('Smart Meter')
    sale_bei = fields.Boolean('BEI')
    sale_ebilling = fields.Boolean('E-Billing')
    salesman_id = fields.Many2one('res.users', string='Sales Agent')
    sale_new_sales_agent = fields.Many2one(
        'res.users', string='New Sales Agent')
    sale_description = fields.Char('Description', related='categ_id.name')
    sale_action = fields.Char('Action ID Stored')
    sale_boolean = fields.Boolean('Boolean for Domain')
    sale_document_recieved_date = fields.Datetime('Recieved')
    sale_document_sent_date = fields.Datetime('Sent')
    sale_usage_type_ratio = fields.Integer("Usage Type Ratio", default=100)
    sale_meter_surcharge = fields.Float('Meter Surcharge')
    sale_previous_contract_end_date = fields.Date(
        string='Previous Contract End Date')
    sale_split_contract = fields.Boolean('Split Contract')
    sale_dd_collection_date = fields.Selection([
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
        ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'),
        ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'),
        ('15', '15'), ('16', '16'), ('17', '17'), ('18', '18'),
        ('19', '19'), ('20', '20'), ('21', '21'), ('22', '22'),
        ('23', '23'), ('24', '24'), ('25', '25'), ('26', '26'),
        ('27', '27'), ('28', '28')
    ], 'DD Collection Day')
    sale_payment_type_bool = fields.Boolean('Payment Type Boolean')
    sale_water_export = fields.Boolean('Water Export')
    sale_water_export_date = fields.Datetime('Water Export Date')
    new_sale_user_id = fields.Many2one('res.users', string='New Sale Agent')
    cleansed_on = fields.Datetime('Cleansed On')
    cleansed_by = fields.Many2one('res.users', string='Cleansed By')
    check_clean = fields.Boolean('Cleansed')
    sale_agent_check = fields.Boolean(
        'Sale Agent Boolean', compute='sale_agent_check_compute')

    # @api.onchange('sale_end_date')
    # def sale_onchange_end_date(self):
    #     if self.sale_end_date:
    #         expiry_date = (datetime.strptime(str(self.sale_end_date),'%Y-%m-%d') - datetime.now()).days
    #         print ('expiry date printed ::>>>>',expiry_date)
    #         exp = (datetime.datetime.strptime(self.sale_end_date, '%Y-%m-%d') - datetime.datetime.today()).days
    #         print ('----printed expiry with expppppp::>>>>>>>>>',exp)
    #     else:
    #         print ('nothing to be printed ::>>>>>>>>>')

    @api.depends('sale_agent_check')
    def sale_agent_check_compute(self):
        for rec in self:
            if self.env.user.has_group('dernetz.group_contract_sys_admin') \
                    or self.env.user.has_group('dernetz.group_contract_admin'):
                rec.sale_agent_check = True
            else:
                rec.sale_agent_check = False

    def sale_export_tick_button(self):
        for rec in self:
            rec.sale_export_flag = True
            rec.sale_export_date = datetime.now()

    def action_send_docusign_wizard(self):

        return {'name': 'Docusign Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'docusign.mail.wiz',
                # 'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                # 'context': {'default_partner_id': rec.sale_partner_id}
                }

    #
    # def action_send_docusign_wizard(self):
    #     ir_model_data = self.env['ir.model.data']
    #     try:
    #         template_id = ir_model_data.get_object_reference('dernetz', 'report_loa_crm_contract')[1]
    #         print ('--printed template id ::>>', template_id)
    #     except ValueError:
    #         template_id = False
    #     try:
    #         compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
    #         print ('--printed compose form id ::>>>', compose_form_id)
    #     except ValueError:
    #         compose_form_id = False
    #     ctx = {
    #         'default_model': 'res.contract',
    #         'default_res_id': self.id,
    #         'default_use_template': bool(template_id),
    #         'default_template_id': template_id,
    #         'default_composition_mode': 'comment',
    #         # 'mark_so_as_sent': True,
    #         # 'custom_layout': "mail.mail_notification_paynow",
    #         # 'proforma': self.env.context.get('proforma', False),
    #         'force_email': True
    #     }
    #     return {
    #         'type': 'ir.actions.act_window',
    #         # 'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form_id, 'form')],
    #         'view_id': compose_form_id,
    #         'target': 'current',
    #         'context': ctx,
    #     }

    @api.onchange('sale_payment_type_id')
    def onchange_payment_term_bool(self):
        for rec in self:
            if rec.sale_payment_type_id:
                rec.sale_payment_type_bool = True
            else:
                rec.sale_payment_type_bool = False

    @api.onchange('utility_type')
    def onchange_product_elec_category(self):
        for rec in self:
            product_elec = self.env['product.category'].search(
                [('name', '=', 'Electricity')])
            product_gas = self.env['product.category'].search(
                [('name', '=', 'Gas')])
            if rec.utility_type == 'ele':
                rec.categ_id = product_elec.id
            elif rec.utility_type == 'gas':
                rec.categ_id = product_gas.id
            else:
                rec.categ_id = False

    @api.depends('sale_supplier_uplift')
    def calculate_sale_supplier_uplift(self):
        for rec in self:
            if rec.sale_supplier_id and rec.sale_supplier_id.name == 'British Gas':
                if rec.sale_contract_type_id and \
                        rec.sale_contract_type_id.name == 'Acquisition':
                    if rec.sale_broker_uplift_value > 0.7:
                        rec.sale_supplier_uplift = rec.sale_broker_uplift_value - 0.7
                elif rec.sale_contract_type_id and \
                        rec.sale_contract_type_id.name in ['Renewal', 'Upgrade']:
                    rec.sale_supplier_uplift = rec.sale_broker_uplift_value
            else:
                rec.sale_supplier_uplift = rec.sale_uplift_value - rec.sale_broker_uplift_value

    @api.depends('sale_end_date')
    def compute_expiry_date(self):
        for rec in self:
            if rec.sale_end_date:
                expiry_date = (datetime.strptime(
                    str(rec.sale_end_date), '%Y-%m-%d') - datetime.now()).days
                print('expiry date printed ::>>>>', expiry_date)
                rec.sale_days_to_expiry = expiry_date

    @api.onchange('check_clean')
    def onchange_check_cleansed(self):
        if self.check_clean:
            self.cleansed_by = self.env.uid
            self.cleansed_on = datetime.now()
        else:
            self.cleansed_by = False
            self.cleansed_on = False

    @api.onchange('sale_export_flag')
    def _onchange_sale_export_date(self):
        for rec in self:
            if rec.sale_export_flag:
                rec.sale_export_date = datetime.now()
            else:
                rec.sale_export_date = ''

    def contract_action_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })
        return True

    def action_verbal(self):
        for self_obj in self:
            view_id = self.env['ir.ui.view'].search(
                [('model', '=', 'contract.verbal.open'),
                 ('name', '=', 'Contract Verbal Open')])
            new_context = {'active_id': self_obj.id,
                           'active_ids': [self_obj.id]}
            default_fields = self.env['contract.verbal.open'] \
                .with_context(new_context).fields_get()
            verbal_default = self.env['contract.verbal.open'] \
                .with_context(new_context).default_get(default_fields)
            res_id = self.env['contract.verbal.open']. \
                with_context(new_context).create(verbal_default)
            if self_obj.partner_id.branch_ids:
                branch_con_ids = self.search(
                    [('partner_id', 'in',
                      [x.id for x in self_obj.partner_id.branch_ids]),
                     ('state', '=', 'draft')],
                )
                if branch_con_ids:
                    res_id.write({'check_branch_contract': True})
                    branch_con_ids.write({'verbal_contract_id': res_id.id})
        return {
            # 'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'contract.verbal.open',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': view_id.id,
            'res_id': res_id.id,
            'context': new_context,
        }

    def action_written(self):
        for this_id in self:
            search_renew_id = self.search(
                [('renew_id', '=', this_id.id)])
            if search_renew_id:
                search_renew_id.write(
                    {'superseded': True,
                     'alert': False,
                     'call_back_list': False,
                     'rec_color': '',
                     'alert_no': 1},
                )
        self.write(
            {'confirmation_medium': 'wri',
             'confirmation_date': fields.Date.context_today(self),
             'state': 'sale_agreed',
             'last_state': 'sale_agreed',
             }
        )
        return True

    def action_electronic(self):
        # wf_service = netsvc.LocalService("workflow")
        for this_id in self:
            # wf_service.trg_validate(uid, 'res.contract', this_id,
            #                         'act_sale_agreed', cr)
            search_renew_id = self.search([('renew_id', '=',
                                            this_id.id)])
            if search_renew_id:
                search_renew_id.write(
                    search_renew_id, {'superseded': True},
                )
        self.write(
            {'confirmation_medium': 'ele',
             'confirmation_date': fields.Date.context_today(self),
             })
        return True

    def action_sale_confirmed(self):
        # print ">>>>>>>>>>>>>>>>>>>"
        for this_obj in self:
            # if not this_obj.via_verbal and not this_obj.via_written and \
            #         not this_obj.via_electronic and not this_obj.state == "docusign_pending":
            #     raise osv.except_osv(('Invalid Data!'), ("You must obtain \
            #         confirmation before this contract can be agreed."))
            if this_obj.state == 'admin_query':
                self.write(
                    {'state': 'sale_agreed',
                     'last_state': 'sale_agreed'})
            else:
                self.write(
                    {'state': 'sale_agreed',
                     'last_state': 'sale_agreed',
                     'confirmation_date': datetime.now(),
                     })
            search_renew_id = this_obj
            # print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>----------------------"
            if search_renew_id:
                search_renew_id.superseded = True
        return True

    def act_confirmed(self):
        for rec in self:
            rec.write({
                'state': 'confirmed',
                'last_state': 'confirmed',
                'admin_user_id': rec.env.uid,
                'date_admin_confirm': time.strftime('%Y-%m-%d'),
            })
        return True

    def act_accepted(self):
        for rec in self:
            if not rec.supplier_ref:
                raise ValidationError(_('Incomplete Data!, You must enter \
                Supplier Ref before this contract can be accepted.'))
            rec.write({
                'state': 'accepted',
                'last_state': 'accepted',
            })
        return True

    def action_live(self):
        for rec in self:
            rec.write({
                'state': 'live',
                'last_state': 'live',

            })
        return True

    def act_complete(self):
        for rec in self:
            res = {
                'livenocis': datetime.now(),
                'state': 'complete',
                'last_state': 'complete',
            }
            print('--print res ::>>>>', res)
            if rec.default_section_id.external_broker:
                rec.update({
                    'commission_date': datetime.now(),
                })
                print(
                    '--print res in if default section id external broker ::>>>>>', res)
            rec.write(res)
        return True

    def action_livenocis_scanned(self):
        for rec in self:
            rec.write({
                'state': 'livenocis_scanned',
                'last_state': 'livenocis_scanned',
            })
        return True

    def action_payment_confirmed(self):
        for rec in self:
            rec.write({
                'state': 'payment_confirmed',
                'last_state': 'payment_confirmed',
            })

    def action_contract_query(self):
        for rec in self:
            return {'name': 'Contract Query',
                    'type': 'ir.actions.act_window',
                    'res_model': 'contract.query',
                    # 'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_contract_id': rec.id,
                                # 'default_query_check': self.sale_query_boolean,
                                # 'default_query_code': 'General Query',
                                # 'default_return_previous_state': True
                                }
                    }

    def action_admin_query(self):
        for rec in self:
            return {'name': 'Contract Query',
                    'type': 'ir.actions.act_window',
                    'res_model': 'contract.query',
                    # 'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_contract_id': rec.id,
                                # 'default_query_check': self.sale_query_boolean,
                                # 'default_query_code': 'General Query',
                                # 'default_return_previous_state': True
                                }
                    }

    def act_query_resolve(self):
        self.write({'state': 'admin_query'})
        return True

    def action_return_to_prev_state(self):
        for rec in self:
            last_state = rec.last_state
            if last_state in ('draft', 'sale_agreed', 'confirmed', 'accepted', 'query'):
                rec.write({
                    'state': last_state,
                    'query_code_id': False,
                })
                return True
            else:
                return False

    def action_cot_cancel(self):
        for this_obj in self:
            search_renew_id = self.search(
                [('renew_id', '=', this_obj.id)])
            if search_renew_id:
                search_renew_id.write({'superseded': False})
                search_renew_id.cron_call()
        self.write({
            'state': 'cot_cancelled',
            'last_state': 'cot_cancelled'
        })
        return True

    def action_cancel(self):
        for this_obj in self:
            search_renew_id = self.search(
                [('renew_id', '=', this_obj.id)])
            if search_renew_id:
                search_renew_id.write(
                    {'superseded': False,
                     'check_renew': False},
                )
                search_renew_id.cron_call()
            docusign_email_id = self.env['docusign.document'].search(
                [('contract_id', '=', this_obj and this_obj.id or
                  False)])
            if docusign_email_id:
                docusign_email_id.write(
                    {'state': 'admin_cancel'})
        self.write({'state': 'cancelled',
                    'last_state': 'cancelled',
                    'cancelled_date': datetime.now(),
                    'query_code_id': False})
        return True

    def action_reset_to_draft(self):
        """ action reset to draft state """
        self.write({'state': 'draft',
                    'last_state': 'draft',
                    'date_admin_confirm': False,
                    'livenocis': False,
                    'docusign_received': False,
                    'docusign_sent_datetime': False,
                    'docusign_received_datetime': False})

        for contract_id in self:
            search_renew_id = self.search([('renew_id', '=',
                                            contract_id.id)])
            print('---search renew id prinnted :::::>>>>', search_renew_id)
            if search_renew_id:
                search_renew_id.write({'check_renew': True})
            docusign_email_id = self.env['docusign.document'].search(
                [('contract_id', '=', contract_id.id)])
            print('----docusign email id printed :::>>>>>', docusign_email_id)
            if docusign_email_id:
                docusign_email_id.write(
                    {'state': 'admin_delete'})
            con_send_email_his_ids = \
                self.env['contract.send.email.history'].search(
                    [('contract_id', '=', contract_id.id)])
            print('---con send email ids printed ::::>>>>',
                  con_send_email_his_ids)
            if con_send_email_his_ids:
                con_send_email_his_ids.unlink()
            contract_id.write({'supplier_ref': '',
                               'confirmation_date': False,
                               'confirmation_medium': False,
                               'admin_pro_user_id': False})
        return True

    def action_renew_contract(self):
        default_sale_type = self.env['contract.account'].search(
            [('name', '=', 'R')])
        contract_type_id = self.env['contract.type'].search(
            [('name', '=', 'Renewal')])
        for rec in self:
            for meter in rec.meter_data_id:
                meter_data = self.env['meter.data.line'].create({
                    'electric_info_line_id': meter.electric_info_line_id.id,
                    'mpan_code': meter.electric_info_line_id.long_mpan,
                    'gas_info_line_id': meter.gas_info_line_id.id,
                    'mpr_code': meter.gas_info_line_id.mprn,

                })
                # Sale Contract Created
                create_contract = self.env['res.contract'].create({
                    'sale_name': self.env['ir.sequence'].search([('name', '=', 'Sale Order')]).next_by_id() or '/',
                    'date_order': rec.start_date,
                    'sale_partner_id': rec.partner_id.id,
                    'sale_start_date': rec.start_date,
                    'sale_uplift_value': rec.uplift_value,
                    'sale_usage': rec.usage,
                    'sale_broker_uplift_value': rec.broker_uplift,
                    'sale_split_contract': rec.split_contract,
                    'sale_smart_meter': rec.smart_meter,
                    'sale_bei': rec.bei,
                    'sale_ebilling': rec.ebilling,
                    'sale_meter_surcharge': rec.meter_surcharge,
                    'sale_payment_type_id':
                        rec.payment_type_id and rec.payment_type_id.id or
                        False,
                    'sale_categ_id': rec.categ_id and rec.categ_id.id or False,
                    'sale_user_id': self.env.uid,
                    'sale_new_sales_agent': rec.previous_user_id and rec.previous_user_id.id or False,
                    'salesman_id': self.env.uid,
                    'sale_account_id': default_sale_type and default_sale_type.id or
                    rec.contract_account_id and rec.contract_account_id.id or False,
                    'sale_contract_type_id': contract_type_id and contract_type_id.id or rec.contract_type_id.id,
                    'meter_data_id': meter_data.id,

                })

                meter_data.update({
                    'contract_id': create_contract.id,
                })
                print('--print contract id ::>>>>>', create_contract)
                self.write({
                    'renew_so_id': create_contract.id,
                    'check_renew': True,
                    'superseded': False
                })

                # view_ref = self.env['ir.model.data'].get_object_reference('dernetz',
                #                                                           'sale_form_view')

                return {
                    'name': 'Sale Order',
                    'view_mode': 'form',
                    'view_id': self.env.ref('dernetz.sale_form_view').id,
                    # 'view_type': 'form',
                    'res_model': 'res.contract',
                    'res_id': create_contract.id,
                    'type': 'ir.actions.act_window',
                    # 'nodestroy': True,
                    'target': 'current',
                    'domain': '[]',
                }

    # below methods are for sale view
    def action_sale_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })
        return True

    def action_sale_sent(self):
        for rec in self:
            rec.write({
                'state': 'sent'
            })
        return True

    def action_sale_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel'
            })
        return True

    def create_contract(self):
        view_id = self.env.ref('dernetz.contract_form_view', False)
        for rec in self:
            rec.write({
                'state': 'draft',
                'sale_state': 'contract',
                'order_type': 'co',
                'co_boolean': True,
                'sale_contract_id': rec.id,
                'start_date': rec.start_date or False,
                'commission_date': rec.start_date or False,
                'end_date': rec.end_date or False,
                # 'qty': line.product_uom_qty or False,
                # 'uom_id': line.product_uom.id or False,
                'usage': rec.sale_usage or False,
                'categ_id': rec.sale_categ_id and rec.sale_categ_id.id or False,
                'partner_id': rec.sale_partner_id.id or False,
                'des_partner_id': rec.designated_part_id and
                rec.designated_part_id.id or False,
                'address_id': rec.sale_partner_id.child_ids and
                              rec.sale_partner_id.child_ids[0].id or False,
                'user_id': add_user or False,
                'previous_user_id': pre_user or False,
                'sale_name': line.order_id.id or False,
                'supplier_id': rec.sale_supplier_id.id or False,
                # 'previous_supplier_id': rec.previous_supplier_id and
                #                         line.previous_supplier_id.id or False,
                'previous_contract_end_date':
                    rec.sale_previous_contract_end_date or False,
                'uplift_value': rec.sale_uplift_value or False,
                'split_contract': rec.sale_split_contract or False,
                'water_export': rec.sale_water_export or False,
                'water_export_date': rec.sale_water_export_date or False,
                # 'utility_type': rec.categ_id and rec.categ_id.name or 'ele',
                'payment_type_id': rec.sale_payment_type_id and
                rec.sale_payment_type_id.id or False,
                # 'proof_of_usage': line.proof_of_usage and
                #                   line.proof_of_usage.id or False,
                'pricing_type': rec.sale_pricing_type and rec.sale_pricing_type.id or False,
                'ebilling': rec.sale_ebilling,
                'dd_collection_date': rec.sale_dd_collection_date or False,
                'broker_uplift': rec.sale_broker_uplift_value or False,
                'supplier_uplift': rec.sale_supplier_uplift or False,
                'contract_type_id': rec.sale_contract_type_id and
                rec.sale_contract_type_id.id or False,
                'contract_account_id': rec.sale_account_id and
                rec.sale_account_id.id or False,
                'payment_type_bool': rec.sale_payment_type_bool or False,
                'bei': rec.sale_bei,
                'smart_meter': rec.sale_smart_meter,
                'year_duration': rec.sale_year_duration,
                # 'dataref': order.internal_ref or False,
                'general_note': [(6, 0, [x.id for x in rec.general_note_contract_ids])],
                'meter_surcharge': rec.sale_meter_surcharge,
                'contract_subtype_id': rec.contract_subtype_id.id or False,
                'default_section_id': rec.section_id and
                rec.section_id.id or False,
                # 'clean_user_id': line.check_clean and
                #                  (line.clean_user_id and line.clean_user_id.id or False) or
                #                  False,
                # 'clean_datetime': line.check_clean and line.clean_datetime or
                #                   False,
            })

        return {
            'name': 'Contract',
            'res_model': 'res.contract',
            'domain': [],
            # 'context': dict(self._context),
            'type': 'ir.actions.act_window',
            'target': 'current',
            'views': [(view_id.id, 'form')],
            'view_id': view_id.id,
            'res_id': self.id,
        }

    def _check_meter_line(self):
        if 'so_dup' in self._context:
            return True
        if 'cron_call' not in self._context and 'copy_quoat' not in self._context:
            list_code = []
            for contract in self:
                for line in contract.meter_data_line:
                    list_code.append(line.mpan_code)
            if len(list_code) != len(set(list_code)):
                return False
        return True

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        categ_id = self.categ_id
        if categ_id.edit_broker_commission:
            self.edit_broker_commission = categ_id.edit_broker_commission
        if categ_id.edit_internal_commission:
            self.edit_internal_commission = categ_id.edit_internal_commission

    @api.onchange('start_date', 'year_duration', 'default_section_id')
    def onchange_start_date(self):
        for rec in self:
            commission_pool = self.env['contract.commission.confi']
            if rec.start_date and rec.year_duration:
                commi_year = commission_pool.search(
                    [('year_duration', '=', rec.year_duration), ('supplier_id', '=', rec.supplier_id.id),
                     ('external_broker', '=', False)])
                print('---print commission year ::::>>', commi_year)
                end_date = datetime.strptime(str(rec.start_date),
                                             "%Y-%m-%d") + \
                    relativedelta(years=+int(rec.year_duration),
                                  days=-1)
                rec.end_date = end_date.strftime('%Y-%m-%d')
                rec.commi_year_id = commi_year and commi_year.id
                rec.commission_percentage = commi_year and commi_year.percentage

            if rec.default_section_id.external_broker:
                commi_ext_year = commission_pool.sudo().search(
                    [('year_duration', '=', rec.year_duration),
                     ('supplier_id', '=', rec.supplier_id.id),
                     ('external_broker', '=', rec.default_section_id.external_broker)])
                print('--print commission extr year :::>>>>', commi_ext_year)
                rec.broker_commi_year_id = commi_ext_year and commi_ext_year.id
                rec.broker_commission_percentage = commi_ext_year and commi_ext_year.percentage
            elif rec.start_date:
                rec.commission_date = str(rec.start_date)

    @api.onchange('sale_start_date', 'sale_year_duration')
    def onchange_sale_start_date(self):
        for rec in self:
            if rec.sale_start_date and rec.sale_year_duration:
                sale_end_date = datetime.strptime(str(rec.sale_start_date),
                                                  "%Y-%m-%d") + \
                    relativedelta(years=+int(rec.sale_year_duration),
                                  days=-1)
                rec.sale_end_date = sale_end_date.strftime('%Y-%m-%d')

    @api.onchange('sale_confirmed_letter_sent')
    def onchange_sale_confirmed_date(self):
        if self.sale_confirmed_letter_sent:
            self.sale_confirmed_date = time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.sale_confirmed_date = False

    @api.onchange('welcome_letter_sent')
    def onchange_welcome_letter_date(self):
        if self.welcome_letter_sent:
            self.welcome_letter_date = time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.welcome_letter_date = False

    def action_update_livenocis_date(self):
        h_date = False
        for record in self:
            for history in record.contract_send_mail_history_line:
                if history.state_to == 'complete':
                    h_date = history.date
            if h_date:
                if record.default_section_id.external_broker:
                    record.write(
                        {'livenocis': h_date, 'commission_date': h_date})
                else:
                    record.write({'livenocis': h_date,
                                  'commission_date': record.start_date})
            else:
                record.write({'commission_date': record.start_date})
        return True

    @api.onchange('commi_year_id')
    def get_commition_percentage(self):
        if self.commi_year_id:
            self.commission_percentage = self.commi_year_id.percentage
        else:
            self.commi_year_id = 0.0

    @api.onchange('export_flag')
    def onchange_export_flag(self):
        if self.export_flag:
            self.export_date = time.strftime('%Y-%m-%d %H:%M:%S')
            self.export_date_dummy = time.strftime(
                '%Y-%m-%d %H:%M:%S')
        else:
            self.export_date = False
            self.export_date_dummy = False

    @api.onchange('export_flag_2')
    def onchange_export_flag_2(self):
        if self.export_flag_2:
            self.export_date_2 = time.strftime('%Y-%m-%d %H:%M:%S')
            self.export_date_2_dummy = time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.export_date_2 = False
            self.export_date_2_dummy = False

    @api.onchange('export_flag_3')
    def onchange_export_flag_3(self):
        if self.export_flag_3:
            self.export_date_3 = time.strftime('%Y-%m-%d %H:%M:%S')
            self.export_date_3_dummy = time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.export_date_3 = False
            self.export_date_3_dummy = False

    @api.onchange('export_flag_4')
    def onchange_export_flag_4(self):
        if self.export_flag_4:
            self.export_date_4 = time.strftime('%Y-%m-%d %H:%M:%S')
            self.export_date_4_dummy = time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.export_date_4 = False
            self.export_date_4_dummy = False

    def get_current_datetime(self, formatt):
        user = self.env['res.users'].browse(self.env.uid)
        curr_date = datetime.now(
            pytz.timezone(user.partner_id.tz or 'Europe/London'))
        corr_date = curr_date.strftime(formatt)
        return corr_date

    @api.onchange('supplier_id')
    def onchange_supplier(self):
        res = {'value': {}, 'domain': {}}
        final_lst_ids = []
        if self.supplier_id:
            supplier_obj = self.supplier_id
            if supplier_obj.payment_type_ids:
                for payment in supplier_obj.payment_type_ids:
                    final_lst_ids.append(payment.id)
                return {'domain': {'payment_type_id': [('id', 'in',
                                                        final_lst_ids)]}}
        return res

    #
    # def get_all_notes_from_customer(self):
    #     return True

    @api.onchange('uplift_value', 'broker_uplift')
    def onchange_uplift_value(self):
        if self.uplift_value:
            self.broker_uplift = self.uplift_value
        if self.uplift_value and self.broker_uplift:
            self.broker_uplift = self.uplift_value
            self.supplier_uplift = self.uplift_value - self.broker_uplift

    @api.onchange('sale_broker_uplift_value', 'uplift_value')
    def broker_uplift_change(self):
        if self.uplift_value and self.sale_broker_uplift_value:
            self.sale_commission = (
                self.sale_broker_uplift_value * (self.sale_usage or 0.0)) / 100
            self.sale_supplier_uplift = self.sale_uplift_value - self.sale_broker_uplift_value
        else:
            self.supplier_uplift = False

    @api.onchange('utility_type_elec_docusign')
    def _onchange_elec(self):
        if self.utility_type_elec_docusign:
            self.utility_type = 'ele'
        else:
            self.utility_type = ''

    @api.onchange('utility_type_gas_docusign')
    def _onchange_gas(self):
        if self.utility_type_gas_docusign:
            self.utility_type = 'gas'
        else:
            self.utility_type = ''

    def update_uplift_value(self):
        meter_data_obj = self.env['meter.data.line']
        if self.ids:
            for contract in self:
                if contract.meter_data_line:
                    uplift_value = contract.uplift_value
                    for meter_data in contract.meter_data_line:
                        vals = {}
                        vals.update(
                            meter_data.standing_charge_sell_change(

                                meter_data.standing_charge,
                                uplift_value,
                            )['value'])
                        vals.update(
                            meter_data_obj.primary_rate_sell_change(
                                [meter_data.id],
                                meter_data.primary_rate,
                                uplift_value,
                            )['value'])
                        vals.update(
                            meter_data_obj.secondary_rate_sell_change(
                                [meter_data.id],
                                meter_data.secondary_rate,
                                uplift_value,
                            )['value'])
                        vals.update(
                            meter_data_obj.tertiary_rate_sell_change(
                                [meter_data.id],
                                meter_data.tertiary_rate,
                                uplift_value,
                            )['value'])
                        vals.update({'uplift_value': uplift_value})
                        meter_data.write(
                            vals)
        return True

    # @api.onchange('start_date', 'year_duration', 'default_section_id')
    # def onchange_start_date(self):
    #     res = {
    #            'year_duration': self.year_duration,
    #            'commission_date':False,
    #             'end_date': False,
    #             'commi_year_id': False,
    #             'commission_percentage': 0.0,
    #             'dummy_commi_year_id': False,
    #             'dummy_commission_percentage': 0.0,
    #             'broker_commi_year_id': False,
    #             'dummy_broker_commi_year_id': False,
    #             'dummy_broker_commission_percentage': 0.0,
    #             'broker_commission_percentage': 0.0,
    #             }
    #     external_broker = self.default_section_id.external_broker
    #     comm_pool = self.env['contract.commission.confi']
    #     if not self.start_date and self.year_duration:
    #         self.end_date = False
    #     if not self.year_duration:
    #         return {'value': res}
    #
    #     if self.start_date and self.year_duration:
    #         commi_year = comm_pool.search(
    #                                       [('year_duration', '=', self.year_duration),
    # ('supplier_id','=',self.supplier_id.id),
    #                                        ('external_broker', '=', False)])
    #         com_obj = commi_year and \
    #             commi_year[0] or False
    #         end_date = datetime.strptime(str(self.start_date)[:10], '%Y-%m-%d') + \
    #             relativedelta(years=+int(self.year_duration), days=-1)
    #         res.update({
    #                'end_date': self.end_date,
    #                'commi_year_id': com_obj and com_obj.id,
    #                'dummy_commi_year_id': com_obj and com_obj.id,
    #                'dummy_commission_percentage': com_obj and
    #                 com_obj.percentage,
    #                'commission_percentage': com_obj and com_obj.percentage,
    #
    #         })
    #     if external_broker:
    #         commi_ext_year = comm_pool.search(
    #                                       [('year_duration', '=', self.year_duration),
    # ('supplier_id', '=', self.supplier_id.id),
    #                                        ('external_broker', '=', self.external_broker)])
    #         ext_com_obj = commi_ext_year and \
    #                         commi_ext_year[0] or False
    #         res.update({
    #             'broker_commi_year_id': ext_com_obj and ext_com_obj.id,
    #             'dummy_broker_commi_year_id': ext_com_obj and ext_com_obj.id,
    #             'dummy_broker_commission_percentage': ext_com_obj and
    #                                                   ext_com_obj.percentage,
    #             'broker_commission_percentage': ext_com_obj and ext_com_obj.percentage
    #         })
    #     else :
    #         res['commission_date'] = self.start_date
    #     return {'value': res}

    def _compute_meter_data(self):
        for rec in self:
            orders = self.env['meter.data.line'].search(
                [('contract_id', '=', rec.id), ('co_boolean', '=', True)])
            # rec.update({"meter_data" : len(orders.ids)})
            rec.meter_data = len(orders)

    def action_view_meter_data(self):
        order = self.env['meter.data.line'].search(
            [('contract_id', '=', self.id), ('co_boolean', '=', True)])
        print('--print meter data line id ::>>>', order)
        action = self.env.ref('dernetz.meter_data_action_view').read()[0]
        if len(order) == 1:
            action['views'] = [
                (self.env.ref('dernetz.meter_data_views_form').id, 'form')]
            action['res_id'] = order.id
            print('in if condition ::>>>>')
        elif len(order) > 1:
            action['domain'] = [('id', 'in', order.ids)]
            print('in elif condition ::>>')
        else:
            print('in else condition :::>>>')
            return {'name': 'dernetz.meter_data_views_form',
                    # 'view_type': 'form',
                    'view_mode': 'tree',
                    'views': [(self.env.ref('dernetz.meter_data_views_form').id, 'form')],
                    'res_model': 'meter.data.line',
                    'view_id': self.env.ref('dernetz.meter_data_views_form').id,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': {'default_contract_id': self.id, 'default_co_boolean': True,
                                'default_partner_id': self.partner_id.id, 'default_utility_type': self.utility_type}
                    }

        return action

    def _compute_sale_meter_data(self):
        for rec in self:
            orders = self.env['meter.data.line'].search(
                [('contract_id', '=', rec.id), ('so_boolean', '=', True)])
            # rec.update({"meter_data" : len(orders.ids)})
            rec.sale_meter_data = len(orders)

    def action_sale_view_meter_data(self):
        order = self.env['meter.data.line'].search(
            [('contract_id', '=', self.id), ('so_boolean', '=', True)])
        action = self.env.ref('dernetz.meter_data_action_view').read()[0]
        if len(order) == 1:
            action['views'] = [
                (self.env.ref('dernetz.meter_data_views_form').id, 'form')]
            action['res_id'] = order.id
        elif len(order) > 1:
            action['domain'] = [('id', 'in', order.ids)]
        else:
            utility_type = ''
            if self.sale_categ_id.name == 'Electricity':
                utility_type = 'ele'
            elif self.sale_categ_id.name == 'Gas':
                utility_type = 'gas'
            return {'name': 'dernetz.meter_data_views_form',
                    # 'view_type': 'form',
                    'view_mode': 'tree',
                    'views': [(self.env.ref('dernetz.meter_data_views_form').id, 'form')],
                    'res_model': 'meter.data.line',
                    'view_id': self.env.ref('dernetz.meter_data_views_form').id,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': {'default_contract_id': self.id, 'default_so_boolean': True,
                                'default_partner_id': self.sale_partner_id.id, 'default_utility_type':  utility_type}
                    }

        return action

    # Functions for contract commission borker report

    def current_date(self):

        date_now = datetime.now()
        date = date_now.strftime('%d-%m-%Y %H:%M:%S')
        # print ('-----print date with non milli seconds::>>>',date)
        # print ('--print start date :::::::::>>>>>',self.date_from_to()[0].get('start_date'))

        return date

    def date_from_to(self):
        date = []
        date_dict = {
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
        }
        date.append(date_dict)
        # print ("----prin date list :>>>>",date)
        date_string = str(self.start_date) + ' ' + \
            'To' + ' ' + str(self.end_date)
        # print ('----print date stringg full ::>>>>', date_string)

        return date_string

    def default_section(self):
        section = []
        dict_data = {
            'section': self.default_section_id.name,
        }
        section.append(dict_data)
        return section

    def birth_date_child_ids(self):
        for rec in self:
            if rec.partner_id.child_ids:
                child = rec.partner_id.child_ids[0].birth_date
            else:
                child = False
            return child


class ResNote(models.Model):
    _name = "res.note"
    _description = "Res Note"

    admin_note_line_id = fields.Many2one(
        "res.contract", string="Admin Note Line")
    sales_note_line_id = fields.Many2one(
        "res.contract", string="Sales Note Line")

    date = fields.Date(String="Date")
    query_code_id = fields.Many2one('query.code', string="Query Code")
    user_id = fields.Many2one("res.users", string="User")
    name = fields.Char(string="Text")


class BrokerCommissionReconcile(models.Model):
    _name = "broker.commission.reconcile"
    _description = "Broker Commission Reconcile"

    internal_reconcile_line_id = fields.Many2one(
        "res.contract", String="Internal Commission Reconcile")
    external_reconcile_line_id = fields.Many2one(
        "res.contract", String="External Broker Commission Reconcile")

    create_datetime_commission = fields.Datetime(string="Creation Date Time")
    user_id = fields.Many2one("res.users", string="Users")
    receipt_date = fields.Date(string="Adjustment Month")
    receipt_reference = fields.Char(string="Receipt Reference")
    comm_amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)
    is_external_broker = fields.Boolean('Is External Broker')
