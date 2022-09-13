# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os
import json
from odoo import http
from odoo.addons.web.controllers.main import Binary
from odoo.addons.graphql_base import GraphQLControllerMixin
from odoo.http import request, Response
from odoo.tools.safe_eval import safe_eval
from urllib.parse import urlparse

from ..schema import schema


class STBinary(Binary):
    @http.route(['/web/image',
                 '/web/image/<string:xmlid>',
                 '/web/image/<string:xmlid>/<string:filename>',
                 '/web/image/<string:xmlid>/<int:width>x<int:height>',
                 '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<string:model>/<int:id>/<string:field>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
                 '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<int:id>',
                 '/web/image/<int:id>/<string:filename>',
                 '/web/image/<int:id>/<int:width>x<int:height>',
                 '/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
                 '/web/image/<int:id>-<string:unique>',
                 '/web/image/<int:id>-<string:unique>/<string:filename>',
                 '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
                 '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http',
                auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None,
                      **kwargs):
        """ Validate width and height against a whitelist """
        try:
            ICP = request.env['ir.config_parameter'].sudo()
            resize_whitelist = safe_eval(ICP.get_param('stimage_resize_whitelist', '[]'))

            if resize_whitelist and width and height and \
                    (int(width) not in resize_whitelist or int(height) not in resize_whitelist):
                return request.not_found()
        except Exception:
            return request.not_found()

        return super(STBinary, self).content_image(
            xmlid=xmlid, model=model, id=id, field=field, filename_field=filename_field, unique=unique,
            filename=filename, mimetype=mimetype, download=download, width=width, height=height, crop=crop,
            access_token=access_token, **kwargs)


class GraphQLController(http.Controller, GraphQLControllerMixin):

    def _set_website_context(self):
        """Set website context based on http_request_host header."""
        try:
            request_host = request.httprequest.headers.environ['HTTP_RESQUEST_HOST']
            website = request.env['website'].search([('domain', 'ilike', request_host)], limit=1)
            if website:
                context = dict(request.context)
                context.update({
                    'website_id': website.id,
                    'lang': website.default_lang_id.code,
                })
                request.context = context

                request_uid = http.request.env.uid
                website_uid = website.sudo().user_id.id

                if request_uid != website_uid \
                        and request.env['res.users'].sudo().browse(request_uid).has_group('base.group_public'):
                    request.uid = website_uid
        except:
            pass

    # The GraphiQL route, providing an IDE for developers
    @http.route("/graphiql/st", auth="user", cors="*")
    def graphiql(self, **kwargs):
        self._set_website_context()
        return self._handle_graphiql_request(schema.graphql_schema)

    # Optional monkey patch, needed to accept application/json GraphQL
    # requests. If you only need to accept GET requests or POST
    # with application/x-www-form-urlencoded content,
    # this is not necessary.
    GraphQLControllerMixin.patch_for_json("^/graphql/st/?$")

    # The graphql route, for applications.
    # Note csrf=False: you may want to apply extra security
    # (such as origin restrictions) to this route.
    @http.route("/graphql/st", auth="public", csrf=False, cors="*")
    def graphql(self, **kwargs):
        self._set_website_context()
        return self._handle_graphql_request(schema.graphql_schema)

    @http.route('/st/categories', type='http', auth='public', csrf=False, cors="*")
    def stcategories(self):
        self._set_website_context()
        website = request.env['website'].get_current_website()

        categories = []

        if website.default_lang_id:
            lang_code = website.default_lang_id.code
            domain = [('website_slug', '!=', False)]

            for category in request.env['product.public.category'].sudo().search(domain):
                category = category.with_context(lang=lang_code)
                categories.append(category.website_slug)

        return Response(
            json.dumps(categories),
            headers={'Content-Type': 'application/json'},
        )

    @http.route('/st/products', type='http', auth='public', csrf=False, cors="*")
    def stproducts(self):
        self._set_website_context()
        website = request.env['website'].get_current_website()

        products = []

        if website.default_lang_id:
            lang_code = website.default_lang_id.code
            domain = [('website_published', '=', True), ('website_slug', '!=', False)]

            for product in request.env['product.template'].sudo().search(domain):
                product = product.with_context(lang=lang_code)

                url_parsed = urlparse(product.website_slug)
                name = os.path.basename(url_parsed.path)
                path = product.website_slug.replace(name, '')

                products.append({
                    'name': name,
                    'path': '{}:slug'.format(path),
                })

        return Response(
            json.dumps(products),
            headers={'Content-Type': 'application/json'},
        )

    @http.route('/st/redirects', type='http', auth='public', csrf=False, cors="*")
    def stredirects(self):
        redirects = []

        for redirect in request.env['website.rewrite'].sudo().search([]):
            redirects.append({
                'from': redirect.url_from,
                'to': redirect.url_to,
            })

        return Response(
            json.dumps(redirects),
            headers={'Content-Type': 'application/json'},
        )