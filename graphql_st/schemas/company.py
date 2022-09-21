# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo import _

from odoo.addons.graphql_st.schemas.objects import (
    SortEnum, Company
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


class CompanyFilterInput(graphene.InputObjectType):
    id = graphene.Int()


class CompanySortInput(graphene.InputObjectType):
    id = SortEnum()


class Companies(graphene.Interface):
    companies = graphene.List(Company)
    total_count = graphene.Int(required=True)


class CompanyList(graphene.ObjectType):
    class Meta:
        interfaces = (Companies,)


class CompanyQuery(graphene.ObjectType):
    company = graphene.Field(
        Company,
        required=True,
        id=graphene.Int(),
    )
    companies = graphene.Field(
        Companies,
        filter=graphene.Argument(CompanyFilterInput, default_value={}),
        current_page=graphene.Int(default_value=1),
        page_size=graphene.Int(default_value=20),
        search=graphene.String(default_value=False),
        sort=graphene.Argument(CompanySortInput, default_value={})
    )

    @staticmethod
    def resolve_company(self, info, id):
        company = info.context['env']['res.company'].search([('id', '=', id)], limit=1)
        if not company:
            raise GraphQLError(_('Company does not exist.'))
        return company

    @staticmethod
    def resolve_companies(self, info, filter, current_page, page_size, search, sort):
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

        Company = env["res.company"]
        total_count = Company.search_count(domain)
        companies = Company.search(domain, limit=page_size, offset=offset, order=order)
        return CompanyList(companies=companies, total_count=total_count)
