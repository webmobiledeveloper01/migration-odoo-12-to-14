# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import osv


class YearsInResident(models.TransientModel):
    _name = 'years.in.resident'
    _description = 'Years In Resident Memory Wizard'

    years_in_resident = fields.Integer(
        'Years in Residence', required=True)
    flag = fields.Boolean('Flag')
    name = fields.Char('Contact name')
    street = fields.Char(
        'Street', size=128)
    street2 = fields.Char(
        'Street2', size=128)
    zip = fields.Char(
        'Post Code', change_default=True, size=24)
    city = fields.Char(
        'City', size=128)
    state_id = fields.Many2one("res.country.state", 'County')
    country_id = fields.Many2one('res.country', 'Country')

    def onchange_years_in_resident(self, years):
        res = {'flag': False}
        warning = ''
        if not years:
            return {'value': res}
        if years <= 3:
            res.update({'flag': True})
        else:
            warn_msg = 'To create Past Address Years In Residence must be \
            less then 3!'
            warning = {'title': 'Warning !', 'message': warn_msg}
        return {'value': res, 'warning': warning}

    
    def get_create_address(self):
        partner_obj = self.env['res.partner']
        this_obj = self

        if this_obj.years_in_resident > 3:
            raise osv.except_osv(
                'Invalid Action!', 'Cannot create Past Address  because of \
                Years In Residence is greater then 3!')

        default_fields = partner_obj.fields_get()
        partner_default = partner_obj.default_get(
             default_fields)

        if self._context['active_ids']:
            for contract in partner_obj.browse(self._context['active_ids']):
                create_address = {
                    'parent_id': self._context['active_ids'][0],
                    'name': this_obj.name,
                    'street': this_obj.street,
                    'street2': this_obj.street2 or False,
                    'zip': this_obj.zip or False,
                    'city': this_obj.city or False,
                    'state_id': this_obj.state_id and this_obj.state_id.id or
                    False,
                    'country_id': this_obj.country_id and
                    this_obj.country_id.id or False,
                    'past_address': 'past',
                    'years_in_residence': this_obj.years_in_resident,
                }
                partner_default.update(create_address)
                partner_obj.create(partner_default)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
