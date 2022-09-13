# -*- coding: utf-8 -*-
# Copyright 2022 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
import odoo
from odoo import _
from odoo.http import request
from odoo.exceptions import UserError
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.graphql_st.schemas.objects import User
import requests
import json

class Login(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    Output = User

    @staticmethod
    def mutate(self, info, email, password):
        env = info.context['env']

        try:
            uid = request.session.authenticate(request.session.db, email, password)
            return env['res.users'].sudo().browse(uid)
        except odoo.exceptions.AccessDenied as e:
            if e.args == odoo.exceptions.AccessDenied().args:
                raise GraphQLError(_('Wrong email or password.'))
            else:
                raise GraphQLError(_(e.args[0]))


class Logout(graphene.Mutation):

    Output = graphene.Boolean

    @staticmethod
    def mutate(self, info):
        request.session.logout()
        return True


class Register(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)

    Output = User

    @staticmethod
    def mutate(self, info, name, email, password):
        env = info.context['env']

        data = {
            'name': name,
            'login': email,
            'password': password,
        }

        if env['res.users'].sudo().search([('login', '=', data['login'])], limit=1):
            raise GraphQLError(_('Another user is already registered using this email address.'))

        env['res.users'].sudo().signup(data)

        return env['res.users'].sudo().search([('login', '=', data['login'])], limit=1)


class ResetPassword(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    Output = User

    @staticmethod
    def mutate(self, info, email):
        env = info.context['env']
        ResUsers = env['res.users'].sudo()
        create_user = info.context.get('create_user', False)
        user = ResUsers.search([('login', '=', email)])
        if not user:
            user = ResUsers.search([('email', '=', email)])
        if len(user) != 1:
            raise GraphQLError(_('Invalid email.'))

        try:
            user.with_context(create_user=create_user).api_action_reset_password()
            return user
        except UserError as e:
            raise GraphQLError(e.name or e.value)
        except SignupError:
            raise GraphQLError(_('Could not reset your password.'))
        except Exception as e:
            raise GraphQLError(str(e))


class ChangePassword(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        new_password = graphene.String(required=True)

    Output = User

    @staticmethod
    def mutate(self, info, token, new_password):
        env = info.context['env']

        data = {
            'password': new_password,
        }

        ResUsers = env['res.users'].sudo()

        try:
            db, login, password = ResUsers.signup(data, token)
            return ResUsers.search([('login', '=', login)], limit=1)
        except UserError as e:
            raise GraphQLError(e.args[0])
        except SignupError:
            raise GraphQLError(_('Could not change your password.'))
        except Exception as e:
            raise GraphQLError(str(e))


class UpdatePassword(graphene.Mutation):
    class Arguments:
        current_password = graphene.String(required=True)
        new_password = graphene.String(required=True)

    Output = User

    @staticmethod
    def mutate(self, info, current_password, new_password):
        env = info.context['env']
        if env.uid:
            user = env['res.users'].search([('id', '=', env.uid)])
            try:
                user._check_credentials(current_password, env)
                user.change_password(current_password, new_password)
                env.cr.commit()
                request.session.authenticate(request.session.db, user.login, new_password)
                return user
            except odoo.exceptions.AccessDenied:
                raise GraphQLError(_('Incorrect password.'))
        else:
            raise GraphQLError(_('You must be logged in.'))


class SendSMS(graphene.Mutation):
    class Arguments:
        cellphone = graphene.String(required=True)
        message = graphene.String(required=True)

    Output = graphene.Boolean

    @staticmethod
    def mutate(self, info, cellphone, message):
        env = info.context['env']
        ICP = env['ir.config_parameter'].sudo()
        apiUrl = ICP.get_param('st_sms_api_url', False)
        apiKey = ICP.get_param('st_sms_api_key', False)
        apiNumber = ICP.get_param('st_sms_number', False)

        try:
            # https://api.genvoice.net/docs/#api-SMS-SendSMSwithoutFrom
            url = apiUrl + '/api/sms/send'
            if apiNumber != "":
                url = url + "/" + apiNumber
            url = url + "/" + cellphone
            print url;
            data = {'text': message, 'sign': 'ST'}
            print data;
            
            headers = {'Content-type': 'application/json', 'x-app-key': apiKey}
            
            r = requests.post(url, data=json.dumps(data), headers=headers)

            if r.status_code == 200:
                return True
            else:
                raise GraphQLError(_('SMS failed.'))
        except Exception as e:
            raise GraphQLError(_(e.args[0]))
            

class SignMutation(graphene.ObjectType):
    login = Login.Field(description='Authenticate user with email and password and retrieves token.')
    logout = Logout.Field(description='Logout user')
    register = Register.Field(description='Register a new user with email, name and password.')
    reset_password = ResetPassword.Field(description="Send change password url to user's email.")
    change_password = ChangePassword.Field(description="Set new user's password with the token from the change "
                                                       "password url received in the email.")
    update_password = UpdatePassword.Field(description="Update user password.")
    send_sms = SendSMS.Field(description="Send SMS.")

