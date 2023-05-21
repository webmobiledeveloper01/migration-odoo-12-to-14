from odoo import api, models, fields


class AddExistingContact(models.TransientModel):
    _name = 'add.existing.contact'
    _description = "Add Existing Contract"

    parent_partner_id = fields.Many2one('res.partner', 'Partner')
    partner_id = fields.Many2one('res.partner', 'Partner', domain=[('customer', '=', True)])

    # _defaults = {
    #     'parent_partner_id': lambda obj, cr, uid, context: context and
    #     context.get('active_id', False) or False,
    # }

    # def fields_view_get(self,
    #                     cr,
    #                     uid,
    #                     view_id=None,
    #                     view_type=False,
    #                     context=None,
    #                     toolbar=False,
    #                     submenu=False):
    #     res = super(add_existing_contact, self).fields_view_get(
    #         cr,
    #         uid,
    #         view_id=view_id,
    #         view_type=view_type,
    #         context=context,
    #         toolbar=toolbar,
    #         submenu=submenu)
    #     if view_type == 'form':
    #         if context and 'active_ids' in context:
    #             self_obj = self.pool.get('res.partner').browse(
    #                 cr, uid, context['active_ids'][0], context=context)
    #             partner_list = []
    #             partner_list.append(self_obj.id)
    #             if self_obj.parent_id:
    #                 partner_list.append(self_obj.parent_id.id)
    #                 if self_obj.parent_id.child_ids:
    #                     for parent_child in self_obj.parent_id.child_ids:
    #                         partner_list.append(parent_child.id)
    #                 if self_obj.parent_id.branch_ids:
    #                     for parent_branch in self_obj.parent_id.branch_ids:
    #                         partner_list.append(parent_branch.id)
    #                         if parent_branch.child_ids:
    #                             for pr_child in parent_branch.child_ids:
    #                                 partner_list.append(pr_child.id)
    #             if self_obj.child_ids:
    #                 for child in self_obj.child_ids:
    #                     partner_list.append(child.id)
    #             if self_obj.branch_ids:
    #                 for branch in self_obj.branch_ids:
    #                     partner_list.append(branch.id)
    #                     if branch.child_ids:
    #                         for br_child in branch.child_ids:
    #                             partner_list.append(br_child.id)
    #             for field in res['fields']:
    #                 if 'partner_id' in field:
    #                     res['fields']['partner_id']['domain'].append(
    #                         ('id', 'in', partner_list))
    #         view_id = self.pool.get('ir.ui.view').search(
    #             cr, uid, [('name', '=', 'add.existing.contact.wizard')])
    #         if view_id and isinstance(view_id, (list, tuple)):
    #             view_id = view_id[0]
    #     return res

    
    def add_exciting_contact(self):
        partner_pool = self.env['res.partner']
        for self_obj in self:
            new_partner_id = partner_pool.copy(
                self_obj.partner_id.id,
                default={'is_company': False})

            new_partner_id.write({
                    'parent_id': self_obj.parent_partner_id.id and
                    self_obj.parent_partner_id.id or False,
                    'type': 'contact',
                    'name': self_obj.partner_id.name
                }
                )
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
