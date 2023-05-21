# -*- coding: utf-8 -*-

import calendar
import json
import time

from odoo import api, models, fields


class WizardSalePerComission(models.TransientModel):
    _name = 'wizard.sale.per.comission'
    _description = 'This Wizard prints Barchart report based on sale per \
    comission'

    month = fields.Selection(
        [('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
         ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
         ('9', 'September'), ('10', 'October'), ('11', 'November'),
         ('12', 'December')], 'Month', required=True, default=lambda *a: str(time.gmtime()[1]))
    year = fields.Integer('Year', required=True, default=lambda *a: time.gmtime()[0])

    def lengthmonth(self, year, month):
        if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or
                                                (year % 400 == 0))):
            return 29
        return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]

    
    def action_calculatation(self):
        res = []
        sale_user_group_id = self.env['res.groups'].search(
            [('name', '=', 'Contract / Salesteam'), ('users', 'in', [self.env.uid])])
        data = self.read(self.ids[0])[0]
        month = data['month']
        year = data['year']
        day = self.lengthmonth(year, month)
        start_date = str(year) + '-' + str(month) + '-' + '01'
        end_date = str(year) + '-' + str(month) + '-' + str(day)
        if sale_user_group_id:
            query = "select count(*) as cnt,confirmation_date as \
                    date,sum(broker_commission) as total_comission \
                    from res_contract \
                    where \
                    user_id= '%s' and \
                    confirmation_date::date >= '%s' and \
                    confirmation_date::date <= '%s' \
                    group by confirmation_date \
                    order by confirmation_date" % (self.env.uid, start_date, end_date)
            self._cr.execute(query)
            rec_data = self._cr.dictfetchall()
        else:
            query = "select count(*) as cnt,confirmation_date as \
                    date,sum(broker_commission) as total_comission from \
                    res_contract where \
                    confirmation_date::date >= '%s' and \
                    confirmation_date::date <= '%s' \
                    group by confirmation_date \
                    order by confirmation_date" % (start_date, end_date)
            self._cr.execute(query)
            rec_data = self._cr.dictfetchall()
        temp = {}
        if rec_data:
            for rec in rec_data:
                temp = {
                    'date': str(rec['date']),
                    'total_count': rec['cnt'] or 0.0,
                    'total_comission': rec['total_comission'] or 0.0,
                }
                res.append(temp)
        return res

    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids)[0]
        month_name = calendar.month_name[data['month']]
        report_data = self.action_calculatation(cr, uid, ids, context=context)

        data.update({'ids': context.get('active_ids', []),
                     'report_data': json.dumps(report_data),
                     'month': month_name,
                     'year': data['year']})
        datas = {
            'ids': context.get('active_ids', []),
            'model': context.get('active_model', False),
            'form': data,
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'sale.per.comission.report.webkit',
            'datas': datas,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
