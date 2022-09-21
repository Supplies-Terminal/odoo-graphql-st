# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo import _

from odoo.addons.graphql_st.schemas.objects import (
    SortEnum, Website
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
        sorting = 'id ASC'

    return sorting


class WebsiteFilterInput(graphene.InputObjectType):
    id = graphene.Int()


class WebsiteSortInput(graphene.InputObjectType):
    id = SortEnum()


class Websites(graphene.Interface):
    websites = graphene.List(Website)
    total_count = graphene.Int(required=True)


class WebsiteList(graphene.ObjectType):
    class Meta:
        interfaces = (Websites,)


class WebsiteQuery(graphene.ObjectType):
    website = graphene.Field(
        Website,
        required=True,
        id=graphene.Int(),
    )
    websites = graphene.Field(
        Websites,
        filter=graphene.Argument(WebsiteFilterInput, default_value={}),
        current_page=graphene.Int(default_value=1),
        page_size=graphene.Int(default_value=20),
        search=graphene.String(default_value=False),
        sort=graphene.Argument(WebsiteSortInput, default_value={})
    )

    @staticmethod
    def resolve_website(self, info, id):
        website = info.context['env']['website'].search([('id', '=', id)], limit=1)
        if not website:
            raise GraphQLError(_('Website does not exist.'))
        return website

    @staticmethod
    def resolve_websites(self, info, filter, current_page, page_size, search, sort):
        env = info.context["env"]
        order = get_search_order(sort)
        domain = []

        if search:
            for srch in search.split(" "):
                domain += [('name', 'ilike', srch)]

        if filter.get('id'):
            domain += [('id', '=', filter['id'])]

        # First offset is 0 but first page is 1
        if current_page > 1:
            offset = (current_page - 1) * page_size
        else:
            offset = 0

        Website = env["website"]
        total_count = Website.search_count(domain)
        websites = Website.search(domain, limit=page_size, offset=offset, order=order)
        return WebsiteList(websites=websites, total_count=total_count)
