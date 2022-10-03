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

        # for table in tables.values():

        #     tableId = 0
        #     # Determine all the cells that belong to this table
        #     table_cells = [cells[cell_id] for cell_id in get_children_ids(table)]

        #     # Determine the table's number of rows and columns
        #     n_rows = max(cell['RowIndex'] for cell in table_cells)
        #     n_cols = max(cell['ColumnIndex'] for cell in table_cells)
        #     products = {}

        #     # Fill in each cell
        #     for cell in table_cells:
        #         cell_contents = [
        #             words[child_id]['Text']
        #             if child_id in words
        #             else selections[child_id]['SelectionStatus']
        #             for child_id in get_children_ids(cell)
        #         ]
        #         i = cell['RowIndex'] - 1
        #         j = cell['ColumnIndex'] - 1

        #         text = ''.join(cell_contents)
                
        #         # get table ID
        #         if (i==0 and j==0):
        #             tableId = int(text.replace('GROUP', ''))
        #         if (j==1 and i>0):
        #             text = text.replace('b', '6');
        #             text = text.replace('q', '9');
        #             text = text.replace('I', '1');
        #             text = text.replace('l', '1');
        #             text = text.replace('L', '1');
        #             text = text.replace('/', '1');
        #             text = text.replace('\\', '1');
        #             text = text.replace('a', '9');
        #             text = text.replace('&', '8');
        #             text = text.replace('f', '5');
        #             text = text.replace('z', '2');      

        #             isNumber = text.isdigit()
        #             textDigit = 0
        #             if isNumber:
        #                 textDigit = int(text)
        #             products[i-1] = {
        #                 'product_id': 0,
        #                 'title': "",
        #                 'number': textDigit,
        #                 'orginal': text,
        #                 'confidence': 'floatval($confidence)',
        #                 'is_number': isNumber
        #             }

        #     # We assume that the first row corresponds to the column names
        #     if tableId>0: 
        #         dataframes[tableId] = products

        # purchaseCardGrid = 	[{"items":[{"product_id":"128","name":"WHITE GROUD TEA2.5KG 10pc","rank":"0","unit":"1 box"},{"product_id":"129","name":"Grass Jelly 3KG/6pc","rank":"0","unit":"Box"},{"product_id":"130","name":"Plum Juice 6pc","rank":"0","unit":"box"},{"product_id":"133","name":"Litchi syrup/2.5KG/6pc","rank":"0","unit":"Box"},{"product_id":"134","name":"Cranberry Syrup 5KG/4pc","rank":"0","unit":"Box"},{"product_id":"135","name":"TARO 3KG/6PC","rank":"0","unit":"Box"},{"product_id":"136","name":"Rose Syrup 5KG/4pc","rank":"0","unit":"Box"},{"product_id":"137","name":"Passion Fruit 5KG/4pc","rank":"0","unit":"Box"},{"product_id":"138","name":"Grape Fruit 5KG/4pc","rank":"0","unit":"Box"},{"product_id":"139","name":"Mango Jam /2.2KG/6pc","rank":"0","unit":"Box"},{"product_id":"208","name":"柠檬汁 Lemon juice","rank":"0","unit":"ea"},{"product_id":"13001","name":"strawberry syrup 4pc","rank":"0","unit":" box"},{"product_id":"13002","name":"peach syrup 6pc","rank":"0","unit":" box"},{"product_id":"13003","name":"Blueberry 6pc","rank":"0","unit":" box"},{"product_id":"13042","name":"Mango Pulp 24/case","rank":"0","unit":"case"},{"product_id":"13053","name":"Coffe jelly","rank":"0","unit":"case"},{"product_id":"13058","name":"Condensed Milk","rank":"0","unit":"Box"},{"product_id":"13104","name":"Pineapple Coconut Jelly 4Kg/6PCS","rank":"0","unit":"case"},{"product_id":"141","name":"MILK POWDER 1KG/20PC","rank":"0","unit":"Box"},{"product_id":"142","name":"BROWN SUGAR POWDER 30KG/1PC","rank":"0","unit":"Box"}]},{"items":[{"name":"MILK POWDER 1KG/20PC","product_id":226,"group_index":0},{"product_id":"143","name":"Matcha Powder1KG/12pc","rank":"0","unit":"Box"},{"product_id":"144","name":"Chocolate powder 1KG/20pc","rank":"0","unit":"Box"},{"product_id":"145","name":"Waffle powder 1KG/20p","rank":"0","unit":"Box"},{"product_id":"147","name":"PUDDING POWDER","rank":"0","unit":"box"},{"product_id":"74950","name":"Lemon jelly powder","rank":"0","unit":"box"},{"product_id":"148","name":"HONEY 6KG/5PC","rank":"0","unit":"Box"},{"product_id":"13043","name":"Redpath Brown Sugar 20/kg","rank":"0","unit":"bag"},{"product_id":"57606","name":"Ginger tea 4KG bottle","rank":"0","unit":"bottle"},{"product_id":"151","name":"BLACK TEA1KG/6PC","rank":"0","unit":"Box"},{"product_id":"152","name":"GREEN TEA 0.6KG/12PC","rank":"0","unit":"Box"},{"product_id":"154","name":"OOLONG TEA0.6KG/12PC","rank":"0","unit":"Box"},{"product_id":"12942","name":"茶袋 TEA BAG","rank":"0","unit":"each"},{"product_id":"70","name":"YAKULT2.5KG","rank":"0","unit":"Box"},{"product_id":"71","name":"BASIL SEED 25PC","rank":"0","unit":"Box"},{"product_id":"72","name":"AGAR BUBBLE 2KG/6PC","rank":"0","unit":"Box"},{"product_id":"73","name":"AGAR JELLY 4kg/6PC","rank":"0","unit":"Box"},{"product_id":"74","name":"PEARL 3KG/6PC","rank":"0","unit":"Box"},{"product_id":"75","name":"RED BEAN3KG/6PC","rank":"0","unit":"Box"},{"product_id":"76","name":"ALOE 3KG/6PC","rank":"0","unit":"Box"}]},{"items":[{"product_id":"98","name":"Waffle cup 1000pc","rank":"0","unit":"Box"},{"product_id":"200","name":"HOT SLEEVE 1000/PC","rank":"0","unit":"box"},{"product_id":"203","name":"660 FOAM CUP 500/PC","rank":"0","unit":"box"},{"product_id":"204","name":"KUNG FU LABEL/100卷","rank":"0","unit":"box"},{"product_id":"12940","name":"透明圆形盖（95口径）2000入","rank":"0","unit":"case"},{"product_id":"13045","name":"FOAM LID","rank":"0","unit":"case"},{"product_id":"13048","name":"500 COOL CUP /1000PC","rank":"0","unit":"each"},{"product_id":"13049","name":"700 Q COOL CUP /1000PC","rank":"0","unit":"each"},{"product_id":"13054","name":"12*23/LARGE STRAW","rank":"0","unit":"Box"},{"product_id":"13473","name":"HOT CUP LID 1000PCS","rank":"0","unit":"Box"},{"product_id":"13474","name":"TAPE","rank":"0","unit":"roll"},{"product_id":"13500","name":"胶带座（含胶带）tape stand with tape","rank":"0","unit":"each"},{"product_id":"13467","name":"Aprons","rank":"0","unit":"Each"},{"product_id":"13293","name":"Seal Ring","rank":"0","unit":"each"},{"product_id":"13521","name":"500PC雪克杯500PC shaker","rank":"0","unit":"each"},{"product_id":"13522","name":"700PC雪克杯700PC shaker","rank":"0","unit":"each"},{"product_id":"13523","name":"塑膠咖啡杓Brown spoon","rank":"0","unit":"each"},{"product_id":"13525","name":"白鐵保溫茶桶(8L)(含貼紙)Tea bucket (8L)","rank":"0","unit":"each"},{"product_id":269,"name":"Condensed Milk"},{"product_id":356,"name":"Scraper for milk foam"}]},{"items":[{"product_id":"13538","name":"百合壺Container","rank":"0","unit":"each"},{"product_id":"79","name":"制服（二代）（女）","rank":"0","unit":"Box"},{"product_id":"80","name":"1 CUP BAG-10KG","rank":"0","unit":"Bag"},{"product_id":"81","name":"2 CUP BAG10KG","rank":"0","unit":"Box"},{"product_id":"82","name":"4 CUP BAG10KG","rank":"0","unit":"Bag"},{"product_id":"84","name":"500 HOT CUP /1000PC","rank":"0","unit":"Box"},{"product_id":"85","name":"600 HOT CUP 1000PC","rank":"0","unit":"Box"},{"product_id":"88","name":"AP PARAFILM /6PC","rank":"0","unit":"Box"},{"product_id":"77","name":"DETERGENT 5KG/4入","rank":"0","unit":"Box"},{"product_id":"13041","name":"2GK 电子秤 SCALE","rank":"0","unit":"Each"},{"product_id":"75782","name":"Mug cup","rank":"0","unit":""},{"product_id":"13507","name":"白鐵匙26cmSteel long spoon (26cm)","rank":"0","unit":"each"},{"product_id":"13040","name":"take out menu","rank":"0","unit":"each"},{"product_id":"13537","name":"果露罐Bottle for fruit syrup","rank":"0","unit":"each"},{"product_id":"13535","name":"玻璃罐-(圓)Glass bottle","rank":"0","unit":"each"},{"product_id":"13534","name":"密封罐(可可粉.抹茶粉)(含貼紙)Air-tight bottle","rank":"0","unit":"each"},{"product_id":"13100","name":"tea blender","rank":"0","unit":"each"},{"product_id":"13292","name":"Hot Ring","rank":"0","unit":"each"},{"product_id":"191","name":"Milk Foam Mixer","rank":"0","unit":"Box"},{"product_id":"69","name":"10GK 电子秤. SCALE","rank":"0","unit":"Box"}]},{"items":[{"product_id":353,"name":"Milk foam jigger"},{"product_id":239,"name":"Milk Foam Mixer"},{"product_id":324,"name":"500量杯Measuring cup (500cc)"},{"product_id":323,"name":"5000量杯Measuring cup (5000cc)"},{"product_id":359,"name":"Bledner cup (yellow)"},{"product_id":325,"name":"100量杯Measuring cup (100cc)"},{"product_id":326,"name":"300量杯Measuring cup (300cc)"},{"product_id":360,"name":"Smoothie cup (clear white)"},{"product_id":350,"name":"4 Cup tray holder"},{"product_id":427,"name":"1 Cup holder"}]},{"items":[]},{"items":[]},{"items":[]},{"items":[]}]

        # for tableId in dataframes.keys():
        #     table = dataframes[tableId]
        #     print(tableId)
        #     for row in table:
        #         print(table[row])
            
        #         # 对照预设采购卡资料
        #         if purchaseCardGrid[tableId - 1]['items'][row]:  #如果存在对应的cell
        #             gridProduct = purchaseCardGrid[tableId - 1]['items'][row]
        #             dataframes[tableId][row]['product_id'] = gridProduct['product_id'];
        #             dataframes[tableId][row]['title'] = gridProduct['name'];

        #             # productInfo = get_info(D('ProductView'), array('id'=>$gridProduct['product_id'],'language_id'=>$lang_id))
        #             # if ($product) { //如果有设置商品
        #             #     $product['product_id'] = $productInfo['id'];
        #             #     $product['title'] = $productInfo['cate_desc_title'];
        #             #     $product['des'] = $productInfo['des'];
        #             #     $product['unit'] = $productInfo['unit'];
        #             #     $product['min_qty'] = $productInfo['min_qty'];
        #             #     $product['sku'] = $productInfo['sku'];
        #             # } else { //没有预设商品
        #             #     $product['product_id'] = $gridProduct['product_id'];
        #             #     $product['hints'] = "No Product";
        #             #     $product['warning'] = 1;
        #             # }
                    
        dataJSON = json.dumps(dataframes)
        return dataJSON
    
class PurchasecardMutation(graphene.ObjectType):
    update_purchasecard = UpdatePurchasecard.Field(description='Set purchase card for a specific supplier')
    ocr_purchasecard = OcrPurchasecard.Field(description='Textract purchase card image')
