# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import boto3
import base64
import uuid
import io

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
        website_id=graphene.Int(default_value=None),
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
        env = info.context["env"]
        user = env['res.users'].search([('id', '=', env.uid)])
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
        
        user = env['res.users'].sudo().browse(uid)
        if not user:
            raise GraphQLError(_('User does not exist.'))

        partner = user.partner_id
        if not partner:
            raise GraphQLError(_('Partner does not exist.'))

        purchasecard = env['st.purchasecard'].search([('member_id', '=', partner.id), ('website_id', '=', website_id)], limit=1)

        if not purchasecard:
            raise GraphQLError(_('Purchase Card does not exist.'))

        if not purchasecard['data']:
            raise GraphQLError(_('Purchase Card is empty.'))

        purchaseCardGrid = json.loads(purchasecard['data'])  
        if not purchaseCardGrid:
            raise GraphQLError(_('Purchase Card is empty.'))

        imageBase64 = image_base64
        s3 = boto3.client('s3',
            aws_access_key_id=awsAccessKeyId,
            aws_secret_access_key=awsSecretAccessKey,
            region_name=regionName
        )
        
        bucket_name = 'purchasecard'
        file_name_with_extention = purchasecard['uuid'] + '.jpg'
        file = io.BytesIO(base64.b64decode(image_base64))
        obj = s3.upload_fileobj(file, bucket_name,file_name_with_extention)
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
                    'Name': file_name_with_extention
                }
            },
            FeatureTypes=[
                'TABLES'
            ]
        )
        print(analyzeDocumentResponse)

        blocks = analyzeDocumentResponse['Blocks']
        print(blocks)

        def map_blocks(blocks, block_type):
            return {
                block['Id']: block
                for block in blocks
                    if block['BlockType'] == block_type
            }

        tables = map_blocks(blocks, 'TABLE')
        cells = map_blocks(blocks, 'CELL')
        words = map_blocks(blocks, 'WORD')
        selections = map_blocks(blocks, 'SELECTION_ELEMENT')

        def get_children_ids(block):
            for rels in block.get('Relationships', []):
                if rels['Type'] == 'CHILD':
                    yield from rels['Ids']

        dataframes = {}

        for table in tables.values():

            tableId = 0
            # Determine all the cells that belong to this table
            table_cells = [cells[cell_id] for cell_id in get_children_ids(table)]

            # Determine the table's number of rows and columns
            n_rows = max(cell['RowIndex'] for cell in table_cells)
            n_cols = max(cell['ColumnIndex'] for cell in table_cells)
            products = {}

            # Fill in each cell
            for cell in table_cells:
                cell_contents = [
                    words[child_id]['Text']
                    if child_id in words
                    else selections[child_id]['SelectionStatus']
                    for child_id in get_children_ids(cell)
                ]
                i = cell['RowIndex'] - 1
                j = cell['ColumnIndex'] - 1

                text = ''.join(cell_contents)
                
                # get table ID
                if (i==0 and j==0):
                    tableId = int(text.replace('GROUP', ''))
                if (j==1 and i>0):
                    text = text.replace('b', '6');
                    text = text.replace('q', '9');
                    text = text.replace('I', '1');
                    text = text.replace('l', '1');
                    text = text.replace('L', '1');
                    text = text.replace('/', '1');
                    text = text.replace('\\', '1');
                    text = text.replace('a', '9');
                    text = text.replace('&', '8');
                    text = text.replace('f', '5');
                    text = text.replace('z', '2');      

                    isNumber = text.isdigit()
                    textDigit = 0
                    if isNumber:
                        textDigit = int(text)
                    products[i-1] = {
                        'product_id': 0,
                        'title': "",
                        'number': textDigit,
                        'orginal': text,
                        'confidence': 'floatval($confidence)',
                        'is_number': isNumber,
                        'hints': '',
                        'warning': 0
                    }

            # We assume that the first row corresponds to the column names
            if tableId>0: 
                dataframes[tableId] = products

        for tableId in dataframes.keys():
            table = dataframes[tableId]
            for row in table:
                # 对照预设采购卡资料
                try:  #如果存在对应的cell
                    gridProduct = purchaseCardGrid[tableId - 1]['items'][row]
                    dataframes[tableId][row]['product_id'] = gridProduct['product_id'];
                    dataframes[tableId][row]['title'] = gridProduct['name'];

                    if not gridProduct['product_id']:
                        dataframes[tableId][row]['hints'] = "No Product";
                        dataframes[tableId][row]['warning'] = 1;
                    else:
                        product = env['product.product'].browse( gridProduct['product_id'])

                        if not product:
                            dataframes[tableId][row]['hints'] = "Product not available";
                            dataframes[tableId][row]['warning'] = 1;
                        else:
                            dataframes[tableId][row]['title'] = product['name'];
                except IndexError as e:
                    print ('not exsits')
                    
        dataJSON = json.dumps(dataframes)
        return dataJSON
    
class PurchasecardMutation(graphene.ObjectType):
    update_purchasecard = UpdatePurchasecard.Field(description='Set purchase card for a specific supplier')
    ocr_purchasecard = OcrPurchasecard.Field(description='Textract purchase card image')
