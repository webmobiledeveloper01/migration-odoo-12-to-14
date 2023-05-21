# -*- coding: utf-8 -*-

from odoo import api, models, fields


class WizMeterBool(models.TransientModel):
    _name = 'wiz.meter.bool'
    _description = 'Wiz Meter Bool'

    
    def action_mdl_bool(self):
        so_line_obj = self.env['sale.order.line']
        md_line_obj = self.env['meter.data.line']
        product_categ_obj = self.env['product.category']
        elec_ids = product_categ_obj.search(
            [('name', '=', 'Electricity')])
        gas_ids = product_categ_obj.search(
            [('name', '=', 'Gas')])

        if elec_ids:
            elec_so_line_ids = so_line_obj.search(
               [('categ_id', '=', elec_ids[0])])
            if elec_so_line_ids:
                elec_mdl_ids = md_line_obj.search(
                     [('sale_order_line_id', 'in', elec_so_line_ids)])
                if elec_mdl_ids:
                    elec_mdl_ids.write({'electricity_bool': True})

        if gas_ids:
            gas_so_line_ids = so_line_obj.search(
                [('categ_id', '=', gas_ids[0])])
            if gas_so_line_ids:
                gas_mdl_ids = md_line_obj.search(
                    [('sale_order_line_id', 'in', gas_so_line_ids)],
                    )
                if gas_mdl_ids:
                    gas_mdl_ids.write(
                       {'gas_bool': True},
                       )
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
