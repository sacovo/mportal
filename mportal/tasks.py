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
from __future__ import absolute_import
import datetime
from celery import shared_task
from twilio.rest import Client
from webob.multidict import MultiDict

from premailer import transform

from django.core import serializers, mail
from django.core.mail import EmailMultiAlternatives as EmailMessage
from django.template import Template, Context, Engine
from django.conf import settings

import requests
import bleach
from mportal.models import Member, SMSSender, MailGunUser,\
    MailGunMessage, Group, MailTemplate, SMS


@shared_task
def send_sms(content, recipients, group):
    """Sends a sms to all recipients"""
    sender = SMSSender.objects.get(group__pk=group)
    auth = sender.auth
    sid = sender.sid
    user = sender.username
    client = Client(user, auth, user)
    failed = False
    for recipient in serializers.deserialize("json", recipients):
        try:
            number = recipient.object.get_mobile
            if number:
                cont = content.format(member=recipient.object)
                message = client.messages.create(body=cont, to=number,
                                                 from_=sender.number,
                                                 messaging_service_sid=sender.sid,
                                                 status_callback=settings.TWILIO_CALLBACK_URL)
                SMS.objects.create(
                        content=cont,
                        member=recipient.object,
                        incoming=False,
                        twilio_account=sender,
                        twilio_sid=message.sid,
                        delivered=False
                        )

        except:
            print("Error")
    return failed


def render_html(message, etype, img_url, sender, template):
    """Docstring"""
    print(template)
    engine = Engine.get_default()
    s = MailTemplate.objects.get(pk=template).template.read().decode()
    template = engine.from_string(s)
    html = template.render(Context({
        'message': bleach.clean(message, tags=bleach.sanitizer.ALLOWED_TAGS + ['p'], strip=True),
        'etype': etype,
        'img_url': img_url,
        'from': sender,
    }))
    return transform(html)


@shared_task
def send_mail(content, recipients, attachments):
    """Docstring"""
    mails = []
    for recipient in serializers.deserialize("json", recipients):
        mail_ = EmailMessage(content['subject'])
        message = content['message'].format(member=recipient.object)
        mail_.body = message
        message = render_html(message, content['etype'], content['img_url'],
                              content['sender'], content['template'])
        mail_.attach_alternative(message, 'text/html')
        mail_.from_email = '{name} <{email}>'.format(
            email=content['sender'], name=content['name'])
        mail_.to = [recipient.object.email]
        for att in attachments:
            mail_.attach(att['name'], open(att['path'], 'rb').read())
        mails.append(mail_)

    connection = mail.get_connection()
    for mail_ in mails:
        try:
            connection.send_messages([mail_])
        except:
            pass
    return "Success!"


@shared_task
def check_birthday(info_mail, body_text, subject):
    """TODO"""
    today = datetime.date.today()
    future = today + datetime.timedelta(days=2)
    members = Member.objects.filter(
        birthday__day=future.day, birthday__month=future.month)
    if members.count() == 0:
        return 'No upcomming birthdays!'
    message = EmailMessage(subject=subject)
    template = Template(body_text)
    context = Context({'member_list': members})
    message.body = template.render(context)
    message.to = [info_mail]
    message.from_email = 'JUSO Aargau <info@juso-aargau.ch>'
    message.send()
    return '{x} birthdays sent'.format(x=members.count())


@shared_task
def send_mail_mg(content, recipients, attachments, group):
    """Docstring"""
    mails = []
    print(content)

    mailgun_message = MailGunMessage.objects.create(
        group=Group.objects.get(pk=group),
        content=content['message'],
        tag=content['tag'],
        subject=content['subject'],
        sender=content['sender'],
        click_points=content['click_points'],
        open_points=content['open_points'],
        remove_points=content['remove_points'],
    )

    for recipient in serializers.deserialize("json", recipients):
        m = Member.objects.get(pk=recipient.object.pk)
        m.activity_points -= mailgun_message.remove_points
        m.save()
        mailgun_message.recipients.add(
            Member.objects.get(pk=recipient.object.pk))
        mailgun_message.save()
        mdict = MultiDict()
        mdict.add('from', '{name} <{email}>'.format(
            email=content['sender'], name=content['name']))
        mdict.add('to', recipient.object.email)
        mdict.add('subject', content['subject'])
        mdict.add('o:tag', content['tag'])
        mdict.add('v:message-id', mailgun_message.pk)
        message = content['message'].format(member=recipient.object)
        mdict.add('text', message)
        message = render_html(message, content['tag'], content['img_url'],
                              content['sender'], content['template'])
        mdict.add('html', message)
        mails.append(mdict)

    mg_user = MailGunUser.objects.get(group__pk=group)
    for mail_ in mails:
        print(mail)
        url = "https://api.mailgun.net/v3/{domain}/messages".format(
            domain=mg_user.domain)
        auth = ('api', mg_user.api_key)
        files = []
        for att in attachments:
            files.append(('attachment', open(att['path'], 'rb')))
        requests.post(url, auth=auth, data=mail_, files=files)
        print(url)

    return "Success!"
