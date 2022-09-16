# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo import _
from odoo.http import request

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
        uid = request.session.uid
        env = info.context["env"]
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))
        
        preference = env['st.preference'].search([('member_id', '=', partner.id)], limit=1)
        return preference

    @staticmethod
    def resolve_purchasecard(self, info, supplier_id):
        uid = request.session.uid
        env = info.context["env"]
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('supplier_id', '=', supplier_id)], limit=1)
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
        uid = request.session.uid
        env = info.context["env"]
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        values = {}
        values.update({'data': params['data']})
            
        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('supplier_id', '=', params.supplier_id)], limit=1)
        if not purchasecard:
            purchasecard = StPurchasecard()
            values.update({'uuid': ''})
            values.update({'member_id': partner.id})
            values.update({'supplier_id': params.supplier_id})
            
        purchasecard.write(values)
        return purchasecard

### preference ###
class UpdatePreferenceParams(graphene.InputObjectType):
    preferredLanguage = graphene.String()
    subscribeOrderNotice = graphene.Boolean()
    subscribeOther = graphene.Boolean()
    subscribeTo = graphene.String()

class UpdatePreference(graphene.Mutation):
    class Arguments:
        params = UpdatePreferenceParams(required=True)

    Output = StPreference

    @staticmethod
    def mutate(self, info, params):
        uid = request.session.uid
        env = info.context["env"]
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))
        
        preference = env['st.preference'].search([('member_id', '=', partner.id)], limit=1)
        if not preference:
            preference = StPreference()
            preference.member_id = partner.id

        if params.get('preferredLanguage'):
            preference.preferred_language = params['preferredLanguage']
        if params.get('subscribeOrderNotice'):
            preference.subscribe_order_notice = params['subscribeOrderNotice']
        if params.get('subscribeOther'):
            preference.subscribe_other = params['subscribeOther']
        if params.get('subscribeTo'):
            preference.subscribe_to = params['subscribeTo']


        preference.save();
        return preference
    
class StMutation(graphene.ObjectType):
    update_purchasecard = UpdatePurchasecard.Field(description='Set purchase card for a specific supplier')
    update_Preference = UpdatePreference.Field(description='Update user preferrences on App')
