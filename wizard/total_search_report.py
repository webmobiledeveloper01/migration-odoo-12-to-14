# -*- coding: utf-8 -*-

from odoo import api, models, fields


class WizTotalSearchReport(models.TransientModel):
    _name = "wiz.total.search.report"
    _description = "Search Report"

    user_id = fields.Many2one('res.users', 'User')
    company_id = fields.Many2one('res.company', 'Company')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_all = fields.Boolean('Company All')

    def _check_date(self):
        for rec in self:
            if rec.start_date <= rec.end_date:
                return True
            return False

    # _constraints = [(_check_date, 'End date should be greater or equals to \
    # Start date', ['start_date', 'end_date'])]

    def company_id_changed(self, cr, uid, ids, company_id, context=None):
        res = {}
        if context is None:
            context = {}
        user_obj = self.pool.get('res.users')
        if company_id:
            user_ids = user_obj.search(
                cr, uid, [('company_id', '=', company_id)], context=context)
            res.update({'domain': {'user_id': [('id', 'in', user_ids)]}})
        else:
            res.update({'domain': {'user_id': []}})
        return res

    def get_report(self, cr, uid, ids, context=None):
        # this method return print the report based on selection.
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        user_ids = []
        user_obj = self.pool.get('res.users')
        comapany_obj = self.pool.get('res.company')
        search_line_obj = self.pool.get('total.search.line')
        rec = self.browse(cr, uid, ids[0], context=context)
        start_date = rec.start_date
        end_date = rec.end_date
        new_user_id = []
        unique = []
        if rec.user_id and rec.company_id:
            user_ids = user_obj.search(
                cr,
                uid, [('name', '=', rec.user_id.name),
                      ('company_id', '=', rec.company_id.id)],
                context=context)
            total_search_ids = search_line_obj.search(
                cr,
                uid, [('user_id', 'in', user_ids), ('date', '>=', start_date),
                      ('date', '<=', end_date)],
                context=context)
            for new_user_data in search_line_obj.browse(
                    cr, uid, total_search_ids, context=context):
                new_user_id.append(new_user_data.user_id.id)
            [unique.append(item) for item in new_user_id if item not in unique]
        elif rec.company_id:
            user_ids = user_obj.search(
                cr,
                uid, [('company_id', '=', rec.company_id.id)],
                context=context)
            total_search_ids = search_line_obj.search(
                cr,
                uid, [('user_id', 'in', user_ids), ('date', '>=', start_date),
                      ('date', '<=', end_date)],
                context=context)
            for new_user_data in search_line_obj.browse(
                    cr, uid, total_search_ids, context=context):
                new_user_id.append(new_user_data.user_id.id)
            [unique.append(item) for item in new_user_id if item not in unique]
        elif rec.user_id:
            user_ids = user_obj.search(
                cr, uid, [('name', '=', rec.user_id.name)], context=context)
            total_search_ids = search_line_obj.search(
                cr,
                uid, [('user_id', 'in', user_ids), ('date', '>=', start_date),
                      ('date', '<=', end_date)],
                context=context)
            for new_user_data in search_line_obj.browse(
                    cr, uid, total_search_ids, context=context):
                new_user_id.append(new_user_data.user_id.id)
            [unique.append(item) for item in new_user_id if item not in unique]
        elif rec.company_all:
            company_ids = comapany_obj.search(
                cr, uid, [], order='id', context=context)
            user_ids = user_obj.search(
                cr, uid, [('company_id', 'in', company_ids)], context=context)
            total_search_ids = search_line_obj.search(
                cr,
                uid, [('user_id', 'in', user_ids), ('date', '>=', start_date),
                      ('date', '<=', end_date)],
                context=context)
            for new_user_data in search_line_obj.browse(
                    cr, uid, total_search_ids, context=context):
                new_user_id.append(new_user_data.user_id.id)
            [unique.append(item) for item in new_user_id if item not in unique]
            unique = sorted(unique, key=int)
        if unique:
            datas = {
                'ids': unique or [],
                'model': 'wiz.total.search.report',
                'form': data,
                'context': context,
            }
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'report.utility.user.total.search.webkit',
                    'datas': datas}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
