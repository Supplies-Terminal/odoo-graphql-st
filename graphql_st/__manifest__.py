# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'ST Api',
    'version': '16.0.3.1.0',
    'summary': 'ST API',
    'description': """ST API Integration""",
    'category': 'Website',
    'license': 'LGPL-3',
    'author': 'ST',
    'website': 'https://suppliesterminal.com/',
    'depends': [
        'graphql_base',
        'website_sale_wishlist',
        'website_sale_delivery',
        'auth_signup',
        'contacts',
        'theme_default',
        'website',
        'odoo_enhance_st',
    ],
    'data': [
        'data/website_data.xml',
        'data/mail_template.xml',
        'data/ir_config_parameter_data.xml',
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
        'views/website_views.xml',
    ],
    'demo': [
        'data/demo_product_attribute.xml',
        'data/demo_product_public_category.xml',
        'data/demo_products_women_clothing.xml',
        'data/demo_products_women_shoes.xml',
        'data/demo_products_women_bags.xml',
        'data/demo_products_men_clothing_1.xml',
        'data/demo_products_men_clothing_2.xml',
        'data/demo_products_men_clothing_3.xml',
        'data/demo_products_men_clothing_4.xml',
        'data/demo_products_men_shoes.xml',
    ],
    'installable': True,
    'auto_install': False,
}
