from odoo import api, models, fields


class AddGeneralNote(models.TransientModel):
    _name = 'add.general.note'
    _description = "Add General Note"

    query_code_id = fields.Many2one('query.code', 'Query Code')
    name = fields.Text('Note', required=True)

    
    def add_general_note(self):
        contract_rec = self.env['res.contract'].browse(self._context['active_id'])
        for rec in self:
           vals = {
               'query_code_id': rec.query_code_id.id or False,
               'name': rec.name,
               'user_id': self.env.uid,
               'partner_id': contract_rec.partner_id.id or False,
               'contract_id': contract_rec.id,
           }
           self.env['general.note'].sudo().create(vals)
        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
