# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.graphql_st.schemas import (
    country, category, product, order, invoice,
    user_profile, sign,
    address, wishlist, shop, preference, purchasecard, website
)


class Query(
    OdooObjectType,
    country.CountryQuery,
    category.CategoryQuery,
    product.ProductQuery,
    order.OrderQuery,
    invoice.InvoiceQuery,
    user_profile.UserProfileQuery,
    address.AddressQuery,
    wishlist.WishlistQuery,
    shop.ShoppingCartQuery,
    preference.PreferenceQuery,
    purchasecard.PurchasecardQuery,
    website.WebsiteQuery,
):
    pass

class Mutation(
    OdooObjectType,
    user_profile.UserProfileMutation,
    sign.SignMutation,
    address.AddressMutation,
    wishlist.WishlistMutation,
    shop.ShopMutation,
    order.OrderMutation,
    preference.PreferenceMutation,
    purchasecard.PurchasecardMutation,
):
    pass

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    types=[
        website.WebsiteList, 
        country.CountryList, 
        category.CategoryList, 
        product.ProductList, 
        product.ProductVariantData, 
        order.OrderList,
        invoice.InvoiceList, 
        wishlist.WishlistData, 
        shop.CartData]
)
