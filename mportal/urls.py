# coding=utf-8
""" This file is part of Sektionsportal.
    Sektionsportal is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Sektionsportal is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Sektionsportal.  If not, see <http://www.gnu.org/licenses/>.
"""
from django.conf.urls import url
import mportal.views
from django.views.generic import RedirectView

urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/admin/")),
    url(r'^send-mail/$', mportal.views.send_mail, name="send-mail"),
    url(r'^send-mail-mg/$', mportal.views.send_mail_mg, name="send-mail-mg"),
    url(r'^chose-template/([0-9+])/$',
        mportal.views.chose_template, name="chose-template"),
    url(r'^render-letter/(?P<template>[0-9+])/$',
        mportal.views.render_letter, name="render-letter"),
    url(r'^export-excel/$', mportal.views.export_excel, name="export-excel"),
    url(r'^send-sms/', mportal.views.send_sms, name="send-sms"),
    url(r'import/', mportal.views._import, name="import"),
    url(r'twilio-callback/', mportal.views.twilio_callback, name="twilio-callback"),
    url(r'mailgun-webhook/', mportal.views.mailgun_webhook, name="mailgun_webhook"),
    url(r'twilio-chose/(?P<member>[0-9]+)/$',
        mportal.views.open_chat, name="chose-sender"),
    url(r'twilio-window/(?P<member>[0-9]+)/(?P<sender>[0-9]+)/$',
        mportal.views.chat_window, name="chat-window"),
    url(r'twilio-conversation/(?P<member>[0-9]+)/(?P<sender>[0-9]+)/$',
        mportal.views.conversation_view, name="conversation-view"),
    url(r'mailgun-report/(?P<pk>[0-9]+)/$',
        mportal.views.mailgun_report, name="mailgun-report"),
    url(r'forms/confirm/(?P<conf>[\w-]+)/$',
        mportal.views.confirm_view, name="form-confirmation"),
    url(r'forms/send-confirmation/$',
        mportal.views.send_form_link, name="send-form-link"),
    url(r'forms/(?P<slug>[\w-]+)/$',
        mportal.views.portalform_view, name="form-view"),
    url(r'results/(?P<slug>[\w-]+)/view/$',
        mportal.views.form_result_view, name="form-result-view"),
]
