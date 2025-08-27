# -*- coding: utf-8 -*-

from odoo import models, fields


class InheritedStockLocation(models.Model):
    _inherit = 'stock.location'

    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    zip = fields.Char(string="Zip")
    city = fields.Char(string="City")
    state_id = fields.Many2one('res.country.state', string="State")
    country_id = fields.Many2one('res.country', string="Country")
    phone_number = fields.Char(string="Phone Number")