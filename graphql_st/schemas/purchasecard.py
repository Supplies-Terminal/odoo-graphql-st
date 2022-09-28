# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import boto3
import base64
import uuid

import graphene
from graphql import GraphQLError
from odoo import _
from odoo.http import request

from odoo.addons.graphql_st.schemas.objects import (
    StPurchasecard
)

class PurchasecardQuery(graphene.ObjectType):
    purchasecard = graphene.Field(
        StPurchasecard,
    )

    @staticmethod
    def resolve_purchasecard(self, info, website_id):
        uid = request.session.uid
        env = info.context["env"]
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('website_id', '=', website_id)], limit=1)
        return purchasecard

class UpdatePurchasecard(graphene.Mutation):
    class Arguments:
        website_id = graphene.Int(required=True)
        json_card = graphene.String(required=True)

    Output = StPurchasecard

    @staticmethod
    def mutate(self, info, website_id, json_card):
        uid = request.session.uid
        env = info.context["env"]
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        values = {}
        values.update({'data': json_card})
            
        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('website_id', '=', website_id)], limit=1)
        if purchasecard:
            purchasecard.write(values)
        else:
            values.update({'uuid': uuid.uuid4()})
            values.update({'member_id': partner.id})
            values.update({'website_id': website_id})
            purchasecard = env['st.purchasecard'].create(values)
            
        return purchasecard

class OcrPurchasecard(graphene.Mutation):
    class Arguments:
        website_id = graphene.Int(required=True)
        image_base64 = graphene.String(required=True)

    Output = graphene.String

    @staticmethod
    def mutate(self, info, website_id, image_base64):
        uid = request.session.uid
        env = info.context["env"]
        ICP = env['ir.config_parameter'].sudo()
        awsAccessKeyId = ICP.get_param('st_aws_access_key_id', "")
        awsSecretAccessKey = ICP.get_param('st_aws_access_key_secret', "")
        regionName = ICP.get_param('st_aws_region', "")
        print(awsAccessKeyId)
        print(awsSecretAccessKey)
        print(regionName)
        
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('website_id', '=', website_id)], limit=1)

        if not purchasecard:
            raise GraphQLError(_('Purchase Card does not exist.'))

        # session = boto3.Session(
        #     aws_access_key_id=awsAccessKeyId,
        #     aws_secret_access_key=awsSecretAccessKey,
        #     region_name=regionName
        # )

        # imageBase64 = image_base64
        # s3 = session.resource('s3')
        bucket_name = 'purchasecard'
        # file_name_with_extention = purchasecard['uuid'] + '.jpg'
        # obj = s3.Object(bucket_name,file_name_with_extention)
        # obj.put(Body=image_base64)
        # location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        # object_url = "https://%s.s3-%s.amazonaws.com/%s" % (bucket_name, location, file_name_with_extention)
        
        # Amazon Textract client
        textractClient = boto3.client('textract',
            aws_access_key_id=awsAccessKeyId,
            aws_secret_access_key=awsSecretAccessKey,
            region_name=regionName
        )

        # Call Amazon Textract
        analyzeDocumentResponse = textractClient.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket_name, 
                    'Name': 'table_no_format.jpg'
                }
            },
            FeatureTypes=[
                'TABLES'
            ]
        )
        print(analyzeDocumentResponse)

        blocks = analyzeDocumentResponse['Blocks']
        print(blocks)

        # tables = [] # 所有tables
        # allWords = [] # 所有类别
        # allCells = []
        
        dataJSON = json.dumps(blocks)
        return dataJSON
    
class PurchasecardMutation(graphene.ObjectType):
    update_purchasecard = UpdatePurchasecard.Field(description='Set purchase card for a specific supplier')
    ocr_purchasecard = OcrPurchasecard.Field(description='Textract purchase card image')
