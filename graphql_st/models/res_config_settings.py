# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import uuid
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    st_payment_success_return_url = fields.Char(
        'Payment Success Return Url', related='website_id.st_payment_success_return_url', readonly=False,
        required=True
    )
    st_payment_error_return_url = fields.Char(
        'Payment Error Return Url', related='website_id.st_payment_error_return_url', readonly=False,
        required=True
    )

    st_sms_api_url = fields.Char('SMS API Url', required=True)
    st_sms_api_key = fields.Char('SMS API Key', required=True)
    st_sms_number = fields.Char('SMS API Out Number', required=False)

    st_aws_access_key_id = fields.Char('Access Key ID', required=True)
    st_aws_access_key_secret = fields.Char('Access Key Secret', required=True)
    st_aws_region = fields.Char('Region ', required=True)

    st_cache_invalidation_key = fields.Char('Cache Invalidation Key', required=True)
    st_cache_invalidation_url = fields.Char('Cache Invalidation Url', required=True)

    # ST Images
    st_image_quality = fields.Integer('Quality', required=True)
    st_image_background_rgba = fields.Char('Background RGBA', required=True)
    st_image_resize_whitelist = fields.Char('Resize Whitelist', required=True,
                                             help='Allowed pixel values to resize image for width and height')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            st_sms_api_url=ICP.get_param('st_sms_api_url'),
            st_sms_api_key=ICP.get_param('st_sms_api_key'),
            st_sms_number=ICP.get_param('st_sms_number'),
            st_aws_access_key_id=ICP.get_param('st_aws_access_key_id'),
            st_aws_access_key_secret=ICP.get_param('st_aws_access_key_secret'),
            st_aws_region=ICP.get_param('st_aws_region'),
            st_cache_invalidation_key=ICP.get_param('st_cache_invalidation_key'),
            st_cache_invalidation_url=ICP.get_param('st_cache_invalidation_url'),
            st_image_quality=int(ICP.get_param('st_image_quality', 100)),
            st_image_background_rgba=ICP.get_param('st_image_background_rgba', '(255, 255, 255, 255)'),
            st_image_resize_whitelist=ICP.get_param('st_image_resize_whitelist', '[]'),
        )
        return res

    def set_values(self):
        if self.st_image_quality < 0 or self.st_image_quality > 100:
            raise ValidationError(_('Invalid image quality percentage.'))

        st_image_resize_whitelist = safe_eval(self.st_image_resize_whitelist)
        if not isinstance(st_image_resize_whitelist, list):
            raise ValidationError(_('Invalid image resize whitelist.'))

        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('st_sms_api_url', self.st_sms_api_url)
        ICP.set_param('st_sms_api_key', self.st_sms_api_key)
        ICP.set_param('st_sms_number', self.st_sms_number)
        ICP.set_param('st_aws_access_key_id', self.st_aws_access_key_id)
        ICP.set_param('st_aws_access_key_secret', self.st_aws_access_key_secret)
        ICP.set_param('st_aws_region', self.st_aws_region)
        ICP.set_param('st_cache_invalidation_key', self.st_cache_invalidation_key)
        ICP.set_param('st_cache_invalidation_url', self.st_cache_invalidation_url)
        ICP.set_param('st_image_quality', self.st_image_quality)
        ICP.set_param('st_image_background_rgba', self.st_image_background_rgba)
        ICP.set_param('st_image_resize_whitelist', sorted(st_image_resize_whitelist))

    @api.model
    def create_st_cache_invalidation_key(self):
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('st_cache_invalidation_key', str(uuid.uuid4()))
