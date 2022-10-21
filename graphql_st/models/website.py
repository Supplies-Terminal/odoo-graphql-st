# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import requests
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.http import request
from odoo.addons.website.models import ir_http
from odoo.addons.http_routing.models.ir_http import url_for

_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = 'website'

    st_payment_success_return_url = fields.Char(
        'Payment Success Return Url', required=True, translate=True, default='Dummy'
    )
    st_payment_error_return_url = fields.Char(
        'Payment Error Return Url', required=True,  translate=True, default='Dummy'
    )
    @api.model
    def enable_b2c_reset_password(self):
        """ Enable sign up and reset password on default website """
        website = self.env.ref('website.default_website', raise_if_not_found=False)
        if website:
            website.auth_signup_uninvited = 'b2c'

        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('auth_signup.invitation_scope', 'b2c')
        ICP.set_param('auth_signup.reset_password', True)

    def _site_sale_get_payment_term(self, website, partner):
        pt = self.env.ref('account.account_payment_term_immediate', False).sudo()
        if pt:
            pt = (not pt.company_id.id or website.company_id.id == pt.company_id.id) and pt
        return (
            partner.property_payment_term_id or
            pt or
            self.env['account.payment.term'].sudo().search([('company_id', '=', website.company_id.id)], limit=1)
        ).id
        
    def _site_prepare_sale_order_values(self, website, partner, pricelist):
        self.ensure_one()
        salesperson_id = website.salesperson_id.id
        addr = partner.address_get(['delivery'])
        default_user_id = partner.parent_id.user_id.id or partner.user_id.id
        # tag 2: requirement collecting
        values = {
            'partner_id': partner.id,
            'pricelist_id': pricelist.id,
            'payment_term_id': self._site_sale_get_payment_term(website, partner),
            'team_id': self.salesteam_id.id or partner.parent_id.team_id.id or partner.team_id.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': addr['delivery'],
            'user_id': salesperson_id or self.salesperson_id.id or default_user_id,
            'website_id': website.id,
            'currency_id': website.currency_id.id,
            'company_id': website.company_id.id,
            'message_partner_ids': [partner.commercial_partner_id.id],
            'tag_ids': [2]
        }
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_sale_note'):
            values['note'] = website.company_id.sale_note or ""

        return values

    def get_cart_order(self, update_pricelist=False):
        """ Return the current sales order after mofications specified by params.
        :param bool force_create: Create sales order if not already existing
        :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
        :returns: browse record for the current sales order
        """
        self.ensure_one()
        partner = self.env.user.partner_id
        check_fpos = False
        
        # 获取该站点最后一张订单（=购物车）
        sale_order = self.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('website_id', '=', request.website.id),
            ('state', '=', 'draft'),
            ('tag_ids', '=', [2]),
        ], order='write_date desc', limit=1)

        # cart creation was requested (either explicitly or to configure a promo code)
        if not sale_order:
            pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id
            
            pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
            so_data = self._site_prepare_sale_order_values(request.website, partner, pricelist)
            so_data['state'] = 'draft'
            sale_order = self.env['sale.order'].with_company(request.website.company_id.id).with_user(SUPERUSER_ID).create(so_data)

            # set fiscal position
            if request.website.partner_id.id != partner.id:
                sale_order.onchange_partner_shipping_id()
            else: # For public user, fiscal position based on geolocation
                country_code = request.session['geoip'].get('country_code')
                if country_code:
                    country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                    sale_order.fiscal_position_id = request.env['account.fiscal.position'].sudo().with_company(request.website.company_id.id)._get_fpos_by_region(country_id)
                else:
                    # if no geolocation, use the public user fp
                    sale_order.onchange_partner_shipping_id()

            request.session['sale_order_id'] = sale_order.id

        # # update the pricelist
        # if update_pricelist:
        #     request.session['website_sale_current_pl'] = pricelist_id
        #     values = {'pricelist_id': pricelist_id}
        #     sale_order.write(values)
        #     for line in sale_order.order_line:
        #         if line.exists():
        #             sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

        return sale_order
    
class WebsiteRewrite(models.Model):
    _inherit = 'website.rewrite'

    def _get_st_tags(self):
        tags = 'WR%s' % self.id
        return tags

    def _st_request_cache_invalidation(self):
        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param('st_cache_invalidation_url', False)
        key = ICP.get_param('st_cache_invalidation_key', False)

        if url and key:
            try:
                for website_rewrite in self:
                    tags = website_rewrite._get_st_tags()

                    # Make the GET request to the /cache-invalidate
                    requests.get(url, params={'key': key, 'tags': tags}, timeout=5)
            except:
                pass

    def write(self, vals):
        res = super(WebsiteRewrite, self).write(vals)
        self._st_request_cache_invalidation()
        return res

    def unlink(self):
        self._st_request_cache_invalidation()
        return super(WebsiteRewrite, self).unlink()

