# ST GraphQL API - Odoo Backend Modules

## Overview

Vuestorefront 2 is a lightning-fast frontend platform for Headless Commerce.
In some situations it's ok to just use an Odoo template and start your website, but some
companies they need and full blown eCommerce platform because their business depends on that.

The Headless platform it decouples your storefront from the content management system and backend.
Odoo is the ultimate open source base ERP with many millions of customers around the globe, so it's the match made in open source heaven.

This is not another sync between Odoo and other eCommerce, data will always be in Odoo only.

## Purpose

You will need these modules installed in your Odoo to publish the GraphQL endpoints that ST needs.

## How to install

- Firstly, ensure that the module file is present in the add-ons directory of the Odoo 
  server ``` git clone --recurse-submodules https://github.com/odoogap/vuestorefront.git  ```
- Update Modules list so that it appears in the UI within Apps store
- Update Modules list so that it appears in the UI within Apps
- Look for the module within Apps and click on Install
- Spin up your store with the [Vuestorefront-Odoo Integration](https://github.com/vuestorefront-community/odoo.git)
- Check [Vuestorefront-Odoo Documentation] (https://docs.vuestorefront.io/odoo/)

## Dependencies

OCA - Odoo Community Association - Base REST

## How to configure

- Go to Website -> Settings -> Vue Storefront
- Settings:
  - Payment Return Url
  - Cache Invalidation Url
  - Cache Invalidation Key
  - Web Base Url

## Support

To report a problem please [contact us](https://www.odoogap.com/page/contactus/).

Commercial support is available, please email [info@odoogap.com](info@odoogap.com)
or call tel:+351 917848501 for further information.



Payment Success Return Url
http://localhost:3000/checkout/thank-you
Payment Error Return Url
http://localhost:3000/checkout/payment-error
Cache Invalidation Key
d0ae2265-0c24-47e9-9571-631644d3e43d
Cache Invalidation Url
http://localhost:3000/cache-invalidate
Vue Storefront SMS API
SMS API Url
http://suppliesterminal.api.genvoice.net
SMS API Key
53f88bc22a4ca1613ddcd1568b4fff02
SMS API Out Number
AWS Access (Textract, S3)
Access Key ID
AKIASNQ3NZMG67JQ2D4Y
Access Key Secret
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
Region
ca-central-1
Vue Storefront Images
Quality
100
 %
Background RGBA
(255, 255, 255, 255)
Resize Whitelist
[128, 140, 176, 180, 200, 216, 236, 256, 288, 422, 644]
