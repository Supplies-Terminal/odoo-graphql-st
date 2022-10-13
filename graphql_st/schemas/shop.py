# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from odoo.addons.graphql_st.schemas.objects import Order, Partner
from odoo.http import request


class Cart(graphene.Interface):
    orders = graphene.List(Order)


class CartData(graphene.ObjectType):
    class Meta:
        interfaces = (Cart,)


class ShoppingCartQuery(graphene.ObjectType):
    cart = graphene.Field(
        Cart,
    )

    @staticmethod
    def resolve_cart(self, info):
        env = info.context["env"]
        # 改为合并多个网站的cart
        # website = env['website'].get_current_website()
        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()
            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)

class CartAddItem(graphene.Mutation):
    class Arguments:
        website_id = graphene.Int(required=True)
        product_id = graphene.Int(required=True)
        quantity = graphene.Int(required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, website_id, product_id, quantity):
        env = info.context["env"]
        # 改为根据参数指定网站
        # website = env['website'].get_current_website()
        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            if website.id == website_id:
                # 写入/更新商品
                order.write({'website_id': website.id})
                order._cart_update(product_id=product_id, add_qty=quantity)

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)


class CartUpdateItem(graphene.Mutation):
    class Arguments:
        website_id = graphene.Int(required=True)
        line_id = graphene.Int(required=True)
        quantity = graphene.Int(required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, website_id, line_id, quantity):
        env = info.context["env"]
        # 改为根据参数指定网站
        # website = env['website'].get_current_website()
        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            if website.id == website_id:
                # 写入/更新商品
                line = order.order_line.filtered(lambda rec: rec.id == line_id)
                # Reset Warning Stock Message always before a new update
                line.warning_stock = ""
                order._cart_update(product_id=line.product_id.id, line_id=line.id, set_qty=quantity)

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)


class CartRemoveItem(graphene.Mutation):
    class Arguments:
        website_id = graphene.Int(required=True)
        line_id = graphene.Int(required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, website_id, line_id):
        env = info.context["env"]
        # 改为根据参数指定网站
        # website = env['website'].get_current_website()

        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            if website.id == website_id:
                # 写入/更新商品
                line = order.order_line.filtered(lambda rec: rec.id == line_id)
                line.unlink()

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)

class CartClear(graphene.Mutation):
    Output = Order

    @staticmethod
    def mutate(self, info):
        env = info.context["env"]
        # 改为根据参数指定网站
        # website = env['website'].get_current_website()
        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()
            order.order_line.sudo().unlink()
            orders.append(order)
        return orders


class SetShippingMethod(graphene.Mutation):
    class Arguments:
        website_id = graphene.Int(required=True)
        shipping_method_id = graphene.Int(required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, website_id, shipping_method_id):
        env = info.context["env"]
        # 改为根据参数指定网站
        # website = env['website'].get_current_website()

        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            if website.id == website_id:
                # 写入/更新商品
                order._check_carrier_quotation(force_carrier_id=shipping_method_id)

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)


# ---------------------------------------------------#
#      Additional Mutations that can be useful       #
# ---------------------------------------------------#

class ProductInput(graphene.InputObjectType):
    id = graphene.Int(required=True)
    website_id = graphene.Int(required=True)
    quantity = graphene.Int(required=True)


class CartLineInput(graphene.InputObjectType):
    id = graphene.Int(required=True)
    website_id = graphene.Int(required=True)
    quantity = graphene.Int(required=True)


class CartAddMultipleItems(graphene.Mutation):
    class Arguments:
        products = graphene.List(ProductInput, default_value={}, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, products):
        env = info.context["env"]
        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            productsInWebsite = filter(lambda rec: rec['website_id'] == website.id, products)
            for product in productsInWebsite:
                product_id = product['id']
                quantity = product['quantity']
                order._cart_update(product_id=product_id, add_qty=quantity)

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)


class CartUpdateMultipleItems(graphene.Mutation):
    class Arguments:
        lines = graphene.List(CartLineInput, default_value={}, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, lines):
        env = info.context["env"]
        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            linesInWebsite = filter(lambda rec: rec['website_id'] == website.id, lines)
            for line in linesInWebsite:
                line_id = line['id']
                quantity = line['quantity']
                line = order.order_line.filtered(lambda rec: rec.id == line_id)
                # Reset Warning Stock Message always before a new update
                line.warning_stock = ""
                order._cart_update(product_id=line.product_id.id, line_id=line.id, set_qty=quantity)

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)


class CartRemoveMultipleItems(graphene.Mutation):
    class Arguments:
        line_ids = graphene.List(graphene.Int, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, line_ids):
        env = info.context["env"]

        websites = env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            linesInWebsite = filter(lambda rec: rec['website_id'] == website.id, lines)
            for line in linesInWebsite:
                line = order.order_line.filtered(lambda rec: rec.id == line_id)
                line.unlink()

            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                orders.append(order)
        return CartData(orders=orders)


class CreateUpdatePartner(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        subscribe_newsletter = graphene.Boolean(required=True)

    Output = Partner

    @staticmethod
    def mutate(self, info, name, email, subscribe_newsletter):
        env = info.context['env']
        website = env['website'].get_current_website()
        request.website = website
        order = website.get_cart_order()

        data = {
            'name': name,
            'email': email,
        }

        partner = order.partner_id

        # Is public user
        user = env['res.users'].search([('partner_id', '=', partner.id), ('active', '=', False)], limit=1)
        if user and user.has_group('base.group_public'):
            partner = env['res.partner'].sudo().create(data)

            order.write({
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
            })
        else:
            order.partner_id.write(data)

        return partner


class ShopMutation(graphene.ObjectType):
    cart_add_item = CartAddItem.Field(description="Add Item")
    cart_update_item = CartUpdateItem.Field(description="Update Item")
    cart_remove_item = CartRemoveItem.Field(description="Remove Item")
    cart_clear = CartClear.Field(description="Cart Clear")
    cart_add_multiple_items = CartAddMultipleItems.Field(description="Add Multiple Items")
    cart_update_multiple_items = CartUpdateMultipleItems.Field(description="Update Multiple Items")
    cart_remove_multiple_items = CartRemoveMultipleItems.Field(description="Remove Multiple Items")
    set_shipping_method = SetShippingMethod.Field(description="Set Shipping Method on Cart")
    create_update_partner = CreateUpdatePartner.Field(description="Create or update a partner for guest checkout")
