# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo import _
from odoo.http import request

from odoo.addons.graphql_st.schemas.objects import (
    StPreference
)

class PreferenceQuery(graphene.ObjectType):
    preference = graphene.Field(
        StPreference
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
        
        values = {}
        if params.get('preferredLanguage'):
            values.update({'preferred_language': params['preferredLanguage']})
        if params.get('subscribeOrderNotice'):
            values.update({'subscribe_order_notice': params['subscribeOrderNotice']})
        if params.get('subscribeOther'):
            values.update({'subscribe_other': params['subscribeOther']})
        if params.get('subscribeTo'):
            values.update({'subscribe_to': params['subscribeTo']})

        preference = env['st.preference'].search([('member_id', '=', partner.id)], limit=1)
        if preference:
            preference.write(values)
        else:
            values.update({'member_id': partner.id})
            preference = env['st.preference'].create(values)

        preference = env['st.preference'].search([('member_id', '=', partner.id)], limit=1)
        return preference


class PreferenceMutation(graphene.ObjectType):
    update_Preference = UpdatePreference.Field(description='Update user preferrences on App')
