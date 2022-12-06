# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo.http import request
from odoo import _

from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSaleWishlist
from odoo.addons.graphql_st.schemas.objects import WishlistItem


class WishlistItems(graphene.Interface):
    wishlist_items = graphene.List(WishlistItem)


class WishlistData(graphene.ObjectType):
    class Meta:
        interfaces = (WishlistItems,)


class WishlistQuery(graphene.ObjectType):
    wishlist_items = graphene.Field(
        WishlistData,
    )

    @staticmethod
    def resolve_wishlist_items(root, info):
        """ Get current user wishlist items """
        env = info.context['env']

        # 改为不根据website来获取
        # website = env['website'].get_current_website()
        # request.website = website
        # wishlist_items = env['product.wishlist'].current()

        wishlist_items = env['product.wishlist'].search([("partner_id", "=", env.user.partner_id.id)])
        wishlist_items.filtered(lambda x: x.sudo().product_id.product_tmpl_id.website_published and x.sudo().product_id.product_tmpl_id.sale_ok)
        
        return WishlistData(wishlist_items=wishlist_items)


class WishlistAddItem(graphene.Mutation):
    class Arguments:
        product_id = graphene.Int(required=True)

    Output = WishlistData

    @staticmethod
    def mutate(self, info, product_id):
        env = info.context["env"]
        

        values = env['product.wishlist'].with_context(display_default_code=False).current()
        if values.filtered(lambda v: v.product_id.id == product_id):
            # Product already exists in the Wishlist
            wishlist_items = env['product.wishlist'].search([("partner_id", "=", env.user.partner_id.id)])
            wishlist_items.filtered(lambda x: x.sudo().product_id.product_tmpl_id.website_published and x.sudo().product_id.product_tmpl_id.sale_ok)

            return WishlistData(wishlist_items=wishlist_items)
        else:
            product = request.env['product.product'].browse(product_id)
            if product and product.website_id:
                request.website = product.website_id
            else:
                website = env['website'].get_current_website()
                request.website = website
            
            WebsiteSaleWishlist().add_to_wishlist(product_id)

            wishlist_items = env['product.wishlist'].search([("partner_id", "=", env.user.partner_id.id)])
            wishlist_items.filtered(lambda x: x.sudo().product_id.product_tmpl_id.website_published and x.sudo().product_id.product_tmpl_id.sale_ok)

            return WishlistData(wishlist_items=wishlist_items)


class WishlistRemoveItem(graphene.Mutation):
    class Arguments:
       wish_id = graphene.Int(required=True)

    Output = WishlistData

    @staticmethod
    def mutate(self, info, wish_id):
        env = info.context['env']
        Wishlist = env['product.wishlist'].sudo()

        wish_id = Wishlist.search([('id', '=', wish_id)], limit=1)
        wish_id.unlink()

        wishlist_items = env['product.wishlist'].search([("partner_id", "=", env.user.partner_id.id)])
        wishlist_items.filtered(lambda x: x.sudo().product_id.product_tmpl_id.website_published and x.sudo().product_id.product_tmpl_id.sale_ok)

        return WishlistData(wishlist_items=wishlist_items)


class WishlistMutation(graphene.ObjectType):
    wishlist_add_item = WishlistAddItem.Field(description="Add Item")
    wishlist_remove_item = WishlistRemoveItem.Field(description="Remove Item")
