# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from itertools import groupby
from operator import itemgetter
from datetime import date


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    available_in_pos = fields.Boolean(string='Available in POS', help='Check if you want this product to appear in the Point of Sale.', default=False)
    to_weight = fields.Boolean(string='To Weigh With Scale', help="Check if the product should be weighted using the hardware scale integration.")
    pos_categ_id = fields.Many2one(
        'pos.category', string='Point of Sale Category',
        help="Category used in the Point of Sale.")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('available_in_pos', '=', True)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_('You cannot delete a product saleable in point of sale while a session is still opened.'))

    @api.onchange('sale_ok')
    def _onchange_sale_ok(self):
        if not self.sale_ok:
            self.available_in_pos = False


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        product_ctx = dict(self.env.context or {}, active_test=False)
        if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
            if self.with_context(product_ctx).search_count([('id', 'in', self.ids), ('product_tmpl_id.available_in_pos', '=', True)]):
                raise UserError(_('You cannot delete a product saleable in point of sale while a session is still opened.'))

    def get_product_info_pos(self, price, quantity, pos_config_id):
        self.ensure_one()
        config = self.env['pos.config'].browse(pos_config_id)

        # Tax related
        taxes = self.taxes_id.compute_all(price, config.currency_id, quantity, self)
        grouped_taxes = {}
        for tax in taxes['taxes']:
            if tax['id'] in grouped_taxes:
                grouped_taxes[tax['id']]['amount'] += tax['amount']/quantity if quantity else 0
            else:
                grouped_taxes[tax['id']] = {
                    'name': tax['name'],
                    'amount': tax['amount']/quantity if quantity else 0
                }

        all_prices = {
            'price_without_tax': taxes['total_excluded']/quantity if quantity else 0,
            'price_with_tax': taxes['total_included']/quantity if quantity else 0,
            'tax_details': list(grouped_taxes.values()),
        }

        # Pricelists
        if config.use_pricelist:
            pricelists = config.available_pricelist_ids
        else:
            pricelists = config.pricelist_id
        price_per_pricelist_id = pricelists._price_get(self, quantity)
        pricelist_list = [{'name': pl.name, 'price': price_per_pricelist_id[pl.id]} for pl in pricelists]

        # Warehouses
        warehouse_list = [
            {'name': w.name,
            'available_quantity': self.with_context({'warehouse': w.id}).qty_available,
            'forecasted_quantity': self.with_context({'warehouse': w.id}).virtual_available,
            'uom': self.uom_name}
            for w in self.env['stock.warehouse'].search([])]

        # Suppliers
        key = itemgetter('partner_id')
        supplier_list = []
        for key, group in groupby(sorted(self.seller_ids, key=key), key=key):
            for s in list(group):
                if not((s.date_start and s.date_start > date.today()) or (s.date_end and s.date_end < date.today()) or (s.min_qty > quantity)):
                    supplier_list.append({
                        'name': s.partner_id.name,
                        'delay': s.delay,
                        'price': s.price
                    })
                    break

        # Variants
        variant_list = [{'name': attribute_line.attribute_id.name,
                         'values': list(map(lambda attr_name: {'name': attr_name, 'search': '%s %s' % (self.name, attr_name)}, attribute_line.value_ids.mapped('name')))}
                        for attribute_line in self.attribute_line_ids]

        return {
            'all_prices': all_prices,
            'pricelists': pricelist_list,
            'warehouses': warehouse_list,
            'suppliers': supplier_list,
            'variants': variant_list
        }

    # added by shoaib
    @api.model
    def check_pos_stock_before_payment(self, order_data, config_id):
        config = self.env['pos.config'].browse(config_id)
        location = config.picking_type_id.default_location_src_id
        insufficient_products = []

        for line in order_data:
            product = self.browse(line['product_id'])
            available_qty = product.with_context(location=location.id).qty_available
            if line['qty'] > available_qty:
                insufficient_products.append({
                    'product_name': product.display_name,
                    'requested_qty': line['qty'],
                    'available_qty': available_qty
                })

        return insufficient_products

    # added by shoaib
    @api.model
    def check_expired_stock_before_payment(self, order_data, config_id):
        config = self.env['pos.config'].browse(config_id)
        location = config.picking_type_id.default_location_src_id
        expired_errors = []

        # Get today's date (as POS order date)
        today = fields.Date.context_today(self)

        for item in order_data:
            product = self.browse(item['product_id'])
            ordered_qty = item['qty']

            # Get expired batches: expiry_date <= today
            expired_batches = self.env['product.batch'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
                ('expiry_date', '<=', today),
                ('active','=', False)
            ])

            expired_qty = sum(batch.qty for batch in expired_batches)

            # total valid qty = total available - expired
            available_qty = product.with_context(location=location.id).qty_available
            valid_qty = available_qty - expired_qty

            if valid_qty <= 0 or ordered_qty > valid_qty:
                expired_errors.append({
                    'product_name': product.display_name,
                    'ordered_qty': ordered_qty,
                    'expired_qty': expired_qty,
                    'valid_qty': max(valid_qty, 0),
                })

        return expired_errors


class UomCateg(models.Model):
    _inherit = 'uom.category'

    is_pos_groupable = fields.Boolean(string='Group Products in POS',
        help="Check if you want to group products of this category in point of sale orders")


class Uom(models.Model):
    _inherit = 'uom.uom'

    is_pos_groupable = fields.Boolean(related='category_id.is_pos_groupable', readonly=False)
