# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import graphene
from graphql import GraphQLError
from odoo.http import request
from odoo import _
from datetime import datetime

_logger = logging.getLogger(__name__)

from odoo.addons.graphql_st.schemas.objects import (
    SortEnum, OrderStage, InvoiceStatus, Order, ShippingMethod,
    get_document_with_check_access,
    get_document_count_with_check_access
)


def get_search_order(sort):
    sorting = ''
    for field, val in sort.items():
        if sorting:
            sorting += ', '
        sorting += '%s %s' % (field, val.value)

    # Add id as last factor so we can consistently get the same results
    if sorting:
        sorting += ', id ASC'
    else:
        sorting = 'date_order DESC'

    return sorting


class OrderFilterInput(graphene.InputObjectType):
    stages = graphene.List(OrderStage)
    invoice_status = graphene.List(InvoiceStatus)
    date_from = graphene.String()
    date_to = graphene.String()


class OrderSortInput(graphene.InputObjectType):
    id = SortEnum()
    date_order = SortEnum()
    name = SortEnum()
    state = SortEnum()


class Orders(graphene.Interface):
    orders = graphene.List(Order)
    total_count = graphene.Int(required=True)


class OrderList(graphene.ObjectType):
    class Meta:
        interfaces = (Orders,)


class OrderQuery(graphene.ObjectType):
    order = graphene.Field(
        Order,
        required=True,
        id=graphene.Int(),
    )
    orders = graphene.Field(
        Orders,
        filter=graphene.Argument(OrderFilterInput, default_value={}),
        current_page=graphene.Int(default_value=1),
        page_size=graphene.Int(default_value=1000),
        sort=graphene.Argument(OrderSortInput, default_value={})
    )
    delivery_methods = graphene.List(
        graphene.NonNull(ShippingMethod)
    )

    @staticmethod
    def resolve_order(self, info, id):
        SaleOrder = info.context['env']['sale.order']
        error_msg = 'Sale Order does not exist.'
        order = get_document_with_check_access(SaleOrder, [('id', '=', id)], error_msg=error_msg)
        if not order:
            raise GraphQLError(_(error_msg))
        return order.sudo()

    @staticmethod
    def resolve_orders(self, info, filter, current_page, page_size, sort):
        env = info.context["env"]
        user = request.env.user
        partner = user.partner_id
        sort_order = get_search_order(sort)
        domain = [
            # ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('partner_id', '=', partner.id), 
            ('tag_ids', 'not in', [2])
        ]

        # Filter by stages or default to sales and done
        if filter.get('stages', False):
            stages = [stage.value for stage in filter['stages']]
            domain += [('state', 'in', stages)]
        else:
            domain += [('state', 'in', ['draft', 'sale', 'done'])]

        # Filter by invoice status
        if filter.get('invoice_status', False):
            invoice_status = [invoice_status.value for invoice_status in filter['invoice_status']]
            domain += [('invoice_status', 'in', invoice_status)]

        if filter.get('date_from', False):
            dateFrom = datetime.strptime(filter['date_from'], '%Y-%m-%d')
            domain += [('date_order', '>=', dateFrom)]

        if filter.get('date_to', False):
            dateTo = datetime.strptime(filter['date_to'], '%Y-%m-%d')
            domain += [('date_order', '<', dateTo)]

        # First offset is 0 but first page is 1
        if current_page > 1:
            offset = (current_page - 1) * page_size
        else:
            offset = 0

        _logger.info("------order search domain-----")
        _logger.info(domain)
                    
        SaleOrder = env["sale.order"].sudo()
#         orders = SaleOrder.sudo().search(domain, order=sort_order, limit=page_size, offset=offset)
#         total_count = SaleOrder.sudo().search_count(domain)
        orders = get_document_with_check_access(SaleOrder, domain, sort_order, page_size, offset,
                                                error_msg='Sale Order does not exist.')
        total_count = get_document_count_with_check_access(SaleOrder, domain)
        return OrderList(orders=orders and orders.sudo() or orders, total_count=total_count)

    @staticmethod
    def resolve_delivery_methods(self, info):
        """ Get all shipping/delivery methods """
        env = info.context['env']
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order()
        return order._get_delivery_methods()


class ApplyCoupon(graphene.Mutation):
    class Arguments:
        promo = graphene.String()

    error = graphene.String()

    @staticmethod
    def mutate(self, info, promo):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)

        coupon_status = env['sale.coupon.apply.code'].sudo().apply_coupon(order, promo)

        return ApplyCoupon(error=coupon_status.get('not_found') or coupon_status.get('error'))


class ApplyGiftCard(graphene.Mutation):
    class Arguments:
        promo = graphene.String()

    error = graphene.String()

    @staticmethod
    def mutate(self, info, promo):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)

        gift_card = env["gift.card"].sudo().search([('code', '=', promo)], limit=1)
        gift_card_status = order._pay_with_gift_card(gift_card)

        return ApplyGiftCard(error=gift_card_status)


class OrderMutation(graphene.ObjectType):
    apply_coupon = ApplyCoupon.Field(description='Apply Coupon')
    apply_gift_card = ApplyGiftCard.Field(description='Apply Gift Card')
