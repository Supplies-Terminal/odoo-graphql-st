# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import graphene
from graphql import GraphQLError
from odoo.addons.graphql_st.schemas.objects import Order, Partner
from odoo.http import request
from odoo import fields

_logger = logging.getLogger(__name__)

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
        websites = env.user.partner_id.website_ids #env['website'].search([], limit=255, offset=0, order='id ASC')  # 获取所有的站点
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
        websites = env.user.partner_id.website_ids  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            if website.id == website_id:
                # 写入/更新商品
                order.write({'website_id': website.id})

                # 根据商品转换计量单位为计费单位
                product = env['product.product'].browse(product_id)

                qty = quantity
                useSecondaryUom = False
                if product and product.secondary_uom_enabled and product.secondary_uom_rate>0:
                    qty = quantity * product.secondary_uom_rate
                    useSecondaryUom = True
                
                if not product.allow_out_of_stock_order:
                    if qty > product.free_qty:
                        if env.lang == 'zh_CN':
                            raise GraphQLError(('库存不足，当前库存为{}').format(product.free_qty))
                        else:
                            raise GraphQLError(('Not enough stock. Current stock is {}').format(product.free_qty))
                    
                orderline = order._cart_update(product_id=product_id, add_qty=qty)
        
                # 补充写入计量数值（其它信息已经通过
                if useSecondaryUom:
                    rec = env['sale.order.line'].sudo().browse(orderline['line_id'])
                    if rec:
                        rec.write({'secondary_qty': quantity})

            # 添加完毕后重新获取一次
            order = website.get_cart_order()
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
        websites = env.user.partner_id.website_ids  # 获取所有的站点
        orders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()

            if website.id == website_id:
                # 写入/更新商品
                line = order.order_line.filtered(lambda rec: rec.id == line_id)
                # Reset Warning Stock Message always before a new update
                line.warning_stock = ""

                # 根据商品转换计量单位为计费单位
                product = env['product.product'].browse(line.product_id.id)
                qty = quantity
                useSecondaryUom = False
                if product and product.secondary_uom_enabled and product.secondary_uom_rate>0:
                    qty = quantity * product.secondary_uom_rate
                    useSecondaryUom = True
                                      
                if not product.allow_out_of_stock_order:
                    if qty > product.free_qty:
                        if env.lang == 'zh_CN':
                            raise GraphQLError(('库存不足，当前库存为 {}').format(product.free_qty))
                        else:
                            raise GraphQLError(('Not enough stock. Current stock is {}').format(product.free_qty))
                    
                orderline = order._cart_update(product_id=line.product_id.id, line_id=line.id, set_qty=qty)

                # 补充写入计量数值（其它信息已经通过
                if useSecondaryUom:
                    rec = env['sale.order.line'].sudo().browse(orderline['line_id'])
                    if rec:
                        rec.write({'secondary_qty': quantity})

            # 添加完毕后重新获取一次
            order = website.get_cart_order()
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

        websites = env.user.partner_id.website_ids  # 获取所有的站点
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
    Output = CartData

    @staticmethod
    def mutate(self, info):
        env = info.context["env"]
        # 改为根据参数指定网站
        # website = env['website'].get_current_website()
        websites = env.user.partner_id.website_ids  # 获取所有的站点
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

        websites = env.user.partner_id.website_ids  # 获取所有的站点
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
        websites = env.user.partner_id.website_ids  # 获取所有的站点
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
        websites = env.user.partner_id.website_ids  # 获取所有的站点
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

        websites = env.user.partner_id.website_ids  # 获取所有的站点
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


class CheckoutInput(graphene.InputObjectType):
    order_id = graphene.Int(required=True)
    delivery_address_id = graphene.Int(required=True)
    delivery_date = graphene.String(required=True)
    delivery_time = graphene.String(required=True)
    delivery_memo = graphene.String(required=True)

class CartCheckout(graphene.Mutation):
    class Arguments:
        orders = graphene.List(CheckoutInput, default_value={}, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, orders):
        env = info.context["env"]
        websites = env.user.partner_id.website_ids  # 获取所有的站点

        for website in websites:
            request.website = website
            order = website.get_cart_order()

            # cart非空才checkout
            if order.order_line:
                ordersInCheckout = list(filter(lambda rec: rec['order_id'] == order.id, orders))
                if (len(ordersInCheckout)>0):
                    # 更新order的tag_ids 和 delivery_time 和 notes (ordersInCheckout[0].)
                    deliveryDateTime = ""
                    if ordersInCheckout[0].delivery_date:
                        deliveryDateTime = ordersInCheckout[0].delivery_date.replace("/", "-")
                        if ordersInCheckout[0].delivery_time:
                            deliveryDateTime = deliveryDateTime + ' ' + ordersInCheckout[0].delivery_time
                        else:
                            deliveryDateTime = deliveryDateTime + ' 23:59:59'
                    if deliveryDateTime:
                        order.write({
                            'tag_ids': [1],
                            'note': order.note + ' ' + ordersInCheckout[0].delivery_memo,
                            'date_order': fields.Datetime.now(),
                            'date_place': fields.Datetime.now(),
                            'commitment_date': deliveryDateTime
                            })
                    else:
                        order.write({
                            'tag_ids': [1],
                            'note': order.note + ' ' + ordersInCheckout[0].delivery_memo,
                            'date_order': fields.Datetime.now(),
                            'date_place': fields.Datetime.now()
                            })

        newOrders = []
        for website in websites:
            request.website = website
            order = website.get_cart_order()
            if order:
                order.order_line.filtered(lambda l: not l.product_id.active).unlink()
                newOrders.append(order)
                
        return CartData(orders=newOrders)

class ShopMutation(graphene.ObjectType):
    cart_add_item = CartAddItem.Field(description="Add Item")
    cart_update_item = CartUpdateItem.Field(description="Update Item")
    cart_remove_item = CartRemoveItem.Field(description="Remove Item")
    cart_clear = CartClear.Field(description="Cart Clear")
    cart_add_multiple_items = CartAddMultipleItems.Field(description="Add Multiple Items")
    cart_update_multiple_items = CartUpdateMultipleItems.Field(description="Update Multiple Items")
    cart_remove_multiple_items = CartRemoveMultipleItems.Field(description="Remove Multiple Items")
    cart_checkout = CartCheckout.Field(description="Place Order")
    set_shipping_method = SetShippingMethod.Field(description="Set Shipping Method on Cart")
    create_update_partner = CreateUpdatePartner.Field(description="Create or update a partner for guest checkout")
