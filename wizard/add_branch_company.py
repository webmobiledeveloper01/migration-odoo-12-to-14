from odoo import api, models, fields


class AddBranchCompany(models.TransientModel):
    _name = 'add.branch.company'
    _description = "Add Branch Company"

    partner_id = fields.Many2one('res.partner', 'Partner')

    
    def add_existing_brnach(self):
        for rec in self:
            partner = self.env['res.partner'].browse(self._context['active_id'])
            for part in partner:
                part.write({
                        'is_company': True,
                        'parent_id': rec.partner_id.id
                    })
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
