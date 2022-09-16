# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo import _

from odoo.addons.graphql_st.schemas.objects import (
    StPreference, StPurchasecard
)

class StQuery(graphene.ObjectType):
    preference = graphene.Field(
        StPreference
    )
    
    purchasecard = graphene.Field(
        StPurchasecard,
        supplier_id = graphene.Int()
    )

    @staticmethod
    def resolve_preference(self, info):
        env = info.context["env"]
        if not env.uid:
            raise GraphQLError(_('You must be logged in.'))

        user = env['res.users'].search([('id', '=', env.uid)])
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        preference = env['st.preference'].search([('member_id', '=', partner)], limit=1)
        return preference

    @staticmethod
    def resolve_purchasecard(self, info, supplier_id):
        env = info.context["env"]
        if not env.uid:
            raise GraphQLError(_('You must be logged in.'))

        user = env['res.users'].search([('id', '=', env.uid)])
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner), ('supplier_id', '=', supplier_id)], limit=1)
        return purchasecard

### purchase card ###
class UpdatePurchasecardParams(graphene.InputObjectType):
    supplier_id = graphene.Int(required=True)
    data = graphene.String(required=True)

class UpdatePurchasecard(graphene.Mutation):
    class Arguments:
        params = UpdatePurchasecardParams()

    Output = StPurchasecard

    @staticmethod
    def mutate(self, info, params):
        partner = request.env.user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        values = {}
        values.update({'data': params['data']})
            
        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner), ('supplier_id', '=', params.supplier_id)], limit=1)
        if not purchasecard:
            purchasecard = StPurchasecard()
            values.update({'uuid': ''})
            values.update({'member_id': partner})
            values.update({'supplier_id': params.supplier_id})
            
        purchasecard.write(values)
        return purchasecard

### preference ###
class UpdatePreferenceParams(graphene.InputObjectType):
    preferred_language = graphene.String()
    subscribe_order_notice = graphene.Boolean()
    subscribe_other = graphene.Boolean()
    subscribe_to = graphene.String()

class UpdatePreference(graphene.Mutation):
    class Arguments:
        params = UpdatePreferenceParams(required=True)

    Output = StPreference

    @staticmethod
    def mutate(self, info, params):
        partner = request.env.user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))
        
        values = {}
        if params.get('preferred_language'):
            values.update({'preferred_language': params['preferred_language']})
        if params.get('subscribe_order_notice'):
            values.update({'subscribe_order_notice': params['subscribe_order_notice']})
        if params.get('subscribe_other'):
            values.update({'subscribe_other': params['subscribe_other']})
        if params.get('subscribe_to'):
            values.update({'subscribe_to': params['subscribe_to']})

        preference = env['st.preference'].search([('member_id', '=', partner)], limit=1)
        if not purchasecard:
            purchasecard = StPreference()
            values.update({'member_id': partner})

        preference.write(values)
        return preference
    
class StMutation(graphene.ObjectType):
    update_purchasecard = UpdatePurchasecard.Field(description='Set purchase card for a specific supplier')
    update_Preference = UpdatePreference.Field(description='Update user preferrences on App')
