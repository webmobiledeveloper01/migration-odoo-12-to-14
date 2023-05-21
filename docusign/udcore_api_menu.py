from odoo import api, fields, models


class UdcoreApiMenu(models.Model):
    _name = "udicore.api.menu"
    _description = "Udicore Api Menu"

    licence_code = fields.Char('LicenceCode')
    mascarade_user = fields.Char('Mascarade User')