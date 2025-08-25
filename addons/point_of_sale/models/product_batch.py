from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# added by shoaib
class ProductBatch(models.Model):
    _name = 'product.batch'
    _description = 'Product Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    location_id = fields.Many2one('stock.location', string='Stock Location', required=True)
    requisition_id = fields.Char(string='Requisitions')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Float(string='Order Quantity', required=True)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id,
                                 required=True)
    stock_date = fields.Date(string='Stock Date', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    active = fields.Boolean(default=True)