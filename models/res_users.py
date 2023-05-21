from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    total_search_line_ids = fields.One2many('total.search.line',
                                             'user_id', 'Search Lines')
    on_sales_wallboard = fields.Boolean('On Sales Wallboard', default=False)
    on_admin_wallboard = fields.Boolean('On Admin Wallboard', default=False)
    old_sys_id = fields.Char('Old System ID', size=64)
    cleanser = fields.Boolean('Cleanser', default=False)
    default_section_id = fields.Many2one('crm.team', string="Default Sales Team")
    dup_id = fields.Integer('Dup ID')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        section_obj = self.pool.get('crm.team')
        ids = []
        members = []
        if self._context.get('broker_agent') and \
                self._context.get('section_id'):
            section_browse = section_obj.\
                browse(self._context.get('section_id'))
            for agent in section_browse.member_ids:
                members.append(agent.id)
            ids = members
            recs = self.search([('id', 'in', ids)], limit=limit)
            return recs.name_get()
        if name:
            recs = self.search([('old_sys_id', '=', name)], limit=limit)
            return recs.name_get()
        if not ids:
            recs = self.search([('name', 'ilike', name)], limit=limit)
            return recs.name_get()
        return super(ResUsers, self).name_search()
