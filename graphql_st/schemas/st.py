# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import boto3
import base64
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
        if purchasecard:
            purchasecard.write(values)
        else:
            values.update({'uuid': ''})
            values.update({'member_id': partner.id})
            values.update({'supplier_id': params.supplier_id})
            purchasecard = env['st.purchasecard'].create(values)
            
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

### purchase card OCR ###
class ocrPurchasecardParams(graphene.InputObjectType):
    supplier_id = graphene.Int(required=True)
    image_base64 = graphene.String(required=True)

class OcrPurchasecard(graphene.Mutation):
    class Arguments:
        params = ocrPurchasecardParams()

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

        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('supplier_id', '=', params.supplier_id)], limit=1)

        if not purchasecard:
            raise GraphQLError(_('Purchase Card does not exist.'))

        imageBase64 = params.image_base64
        
        # Amazon Textract client
        textractClient = boto3.client('textract',
                                aws_access_key_id='AKIASNQ3NZMG2Y3UEBKL',
                                aws_secret_access_key='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',
                                region_name='ca-central-1')
        # Call Amazon Textract
        analyzeDocumentResponse = textractClient.analyze_document(
            Document={
                'Bytes': content
            },
            FeatureTypes=[
                'TABLES'
            ]
        )
        print(analyzeDocumentResponse)

        blocks = analyzeDocumentResponse['Blocks']
        print(analyzeDocumentResponse)

        # tables = [] # 所有tables
        # allWords = [] # 所有类别
        # allCells = []
        
        purchasecard.data = json.encode(blocks)
        return purchasecard
    
class StMutation(graphene.ObjectType):
    update_Preference = UpdatePreference.Field(description='Update user preferrences on App')
    update_purchasecard = UpdatePurchasecard.Field(description='Set purchase card for a specific supplier')
    ocr_purchasecard = OcrPurchasecard.Field(description='Textract purchase card image')
