from odoo import api, fields, models


class ServicesConfiguration(models.Model):
    _name = 'services.configuration'
    _description = "Services Configuration"
    # _order = 'web_url'

    web_url = fields.Char(string='Web Service URL:')
    client_service = fields.Char(string='Client Service')
    user_id = fields.Char(string='UserID')
    password = fields.Char(string='Password')
