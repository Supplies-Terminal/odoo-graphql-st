# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os
import json
import time
from odoo import http
from odoo.addons.web.controllers.main import Binary
from odoo.addons.graphql_base import GraphQLControllerMixin
from odoo.http import request, Root, Response, HttpRequest
from odoo.tools.safe_eval import safe_eval
from odoo.service import security

from urllib.parse import urlparse
import logging

from ..schema import schema

_logger = logging.getLogger(__name__)

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
    @http.route("/graphiql/st", auth="user", cors='*', csrf=False)
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
    @http.route("/graphql/st", auth="public", cors="https://webapp2.suppliesterminal.com", csrf=False, website=True)
    def graphql(self, **kwargs):
        _logger.info("------graphql/st-----")
        
        self._set_website_context()
        resp = self._handle_graphql_request(schema.graphql_schema)

        # resp.headers['Access-Control-Allow-Origin'] = 'https://webapp2.suppliesterminal.com'
        # resp.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        resp.headers['Access-Control-Allow-Credentials'] = 'true'
        # cookies = resp.headers.get('Set-Cookie')
        # _logger.info(cookies)
        # sessionId = resp.cookies.get('session_id')  没有cookies
        _logger.info(resp.headers)
        # resp.headers.add('Set-Cookie', cookie + '; SameSite=None; Secure')
        # resp.set_cookie('cookie2', 'value2', samesite=None, secure=True)
        # resp.headers.add('Set-Cookie','cookie3=value3; SameSite=None; Secure')
        return resp

    @http.route('/st/categories', type='http', auth='public', csrf=False, cors='*')
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



def dispatch(self):
    if self._is_cors_preflight(request.endpoint):
        _logger.info("------ ***** Dispatcher ***** -----")
        headers = {
            'Access-Control-Allow-Origin': request.endpoint.routing['cors'],
            'Access-Control-Max-Age': 60 * 60 * 24,
            'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
        return Response(status=200, headers=headers)

    if request.httprequest.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE') \
            and request.endpoint.routing.get('csrf', True): # csrf checked by default
        token = self.params.pop('csrf_token', None)
        if not self.validate_csrf(token):
            if token is not None:
                _logger.warning("CSRF validation failed on path '%s'",
                                request.httprequest.path)
            else:
                _logger.warning("""No CSRF validation token provided for path '%s'

Odoo URLs are CSRF-protected by default (when accessed with unsafe
HTTP methods). See
https://www.odoo.com/documentation/15.0/developer/reference/addons/http.html#csrf for
more details.

* if this endpoint is accessed through Odoo via py-QWeb form, embed a CSRF
token in the form, Tokens are available via `request.csrf_token()`
can be provided through a hidden input and must be POST-ed named
`csrf_token` e.g. in your form add:

    <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>

* if the form is generated or posted in javascript, the token value is
available as `csrf_token` on `web.core` and as the `csrf_token`
value in the default js-qweb execution context

* if the form is accessed by an external third party (e.g. REST API
endpoint, payment gateway callback) you will need to disable CSRF
protection (and implement your own protection if necessary) by
passing the `csrf=False` parameter to the `route` decorator.
                """, request.httprequest.path)

            raise werkzeug.exceptions.BadRequest('Session expired (invalid CSRF token)')

    r = self._call_function(**self.params)
    if not r:
        r = Response(status=204)  # no content
    return r

HttpRequest.dispatch = dispatch


# def _save_session2(self):
#     _logger.info("------ ***** _save_session2 ***** -----")
#     """ Save a modified session on disk. """
#     sess = self.session

#     if not sess.can_save:
#         return

#     if sess.should_rotate:
#         sess['_geoip'] = self.geoip
#         root.session_store.rotate(sess, self.env)  # it saves
#     elif sess.is_dirty:
#         sess['_geoip'] = self.geoip
#         root.session_store.save(sess)

#     # We must not set the cookie if the session id was specified
#     # using a http header or a GET parameter.
#     # There are two reasons to this:
#     # - When using one of those two means we consider that we are
#     #   overriding the cookie, which means creating a new session on
#     #   top of an already existing session and we don't want to
#     #   create a mess with the 'normal' session (the one using the
#     #   cookie). That is a special feature of the Javascript Session.
#     # - It could allow session fixation attacks.
#     cookie_sid = self.httprequest.cookies.get('session_id')
#     if not sess.is_explicit and (sess.is_dirty or cookie_sid != sess.sid):
#         self.future_response.set_cookie('session_id', sess.sid, max_age=SESSION_LIFETIME, httponly=True, secure=True, samesite=None)
            
# Request._save_session = _save_session2


def get_response2(self, httprequest, result, explicit_session):
    _logger.info("------ ***** get_response2 ***** -----")
    if isinstance(result, Response) and result.is_qweb:
        try:
            result.flatten()
        except Exception as e:
            if request.db:
                result = request.registry['ir.http']._handle_exception(e)
            else:
                raise

    if isinstance(result, (bytes, str)):
        response = Response(result, mimetype='text/html')
    else:
        response = result
        self.set_csp(response)

    save_session = (not request.endpoint) or request.endpoint.routing.get('save_session', True)
    if not save_session:
        return response

    if httprequest.session.should_save:
        if httprequest.session.rotate:
            self.session_store.delete(httprequest.session)
            httprequest.session.sid = self.session_store.generate_key()
            if httprequest.session.uid:
                httprequest.session.session_token = security.compute_session_token(httprequest.session, request.env)
            httprequest.session.modified = True
        self.session_store.save(httprequest.session)
    # We must not set the cookie if the session id was specified using a http header or a GET parameter.
    # There are two reasons to this:
    # - When using one of those two means we consider that we are overriding the cookie, which means creating a new
    #   session on top of an already existing session and we don't want to create a mess with the 'normal' session
    #   (the one using the cookie). That is a special feature of the Session Javascript class.
    # - It could allow session fixation attacks.
    if not explicit_session and hasattr(response, 'set_cookie'):
        _logger.info("------ ***** response.set_cookie ***** -----")
        response.set_cookie(
            'session_id', httprequest.session.sid, max_age=90 * 24 * 60 * 60, httponly=True, secure=True, samesite=None)

        maxAge=90 * 24 * 60 * 60
        end = time.gmtime(time.time() + maxAge)
        expires = time.strftime("%a, %d-%b-%Y %T GMT", end)
        response.headers['Set-Cookie'] = "session_id=" + httprequest.session.sid + "; Expires=" + expires + "; Max-Age=" + maxAge "; Secure; SameSite=None; HttpOnly; Path=/"
    return response

Root.get_response = get_response2