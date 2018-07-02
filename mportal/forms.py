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
import os
from django import forms
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import ugettext as _
from multiupload.fields import MultiFileField
from tinymce.widgets import TinyMCE

from mportal.models import Member, MailTemplate


class EMailForm(forms.Form):
    """Docstring"""

    def __init__(self, *args, **kwargs):
        super(EMailForm, self).__init__(*args, **kwargs)
    name = forms.CharField(label=_("Name"), max_length=50)
    sender = forms.EmailField(label=_("Absender_in"))
    etype = forms.CharField(max_length=100, label=_(
        "Typ (Medienmitteilung, ...)"))
    subject = forms.CharField(max_length=100, label=_("Betreff"))
    img_url = forms.URLField(required=False)
    message = forms.CharField(widget=TinyMCE(attrs={'cols': 150, 'rows': 100}))
    template = forms.ModelChoiceField(
        queryset=MailTemplate.objects.all(), label=_("Template"))
    attach_1 = forms.FileField(required=False)
    attach_2 = forms.FileField(required=False)
    attach_3 = forms.FileField(required=False)


class ImportForm(forms.Form):
    """Docstring"""
    status = forms.ChoiceField(
        label=_("Status"), choices=Member.STATUS_CHOICES)
    contact_list = forms.ChoiceField(label=_("Kontaktliste"))
    import_mapping = forms.ChoiceField(label=_("Verknüpfung"))
    excel = forms.FileField(label=_("Excel"))
    positions = forms.MultipleChoiceField(label=_("Gruppen"), required=False)
    reversion = forms.BooleanField(label=_("Versionsgeschichte"), required=False,
                                   help_text=_("Sollen die Änderungen wieder Rückgängig gemacht werden können?"))
    delete = forms.BooleanField(
        label=_("Löschen"), required=False, initial=True)


def member_fields():
    """Returns a tuple of all fields"""
    return [
        ('om_number', _('OM-Nummer')),
        ('first_name', _('Vorname')),
        ('last_name', _('Name')),
        ('street', _('Strasse')),
        ('plz', _('PLZ')),
        ('city', _('Ort')),
        ('country', _('Land')),
        ('email', _('E-Mail')),
        ('gender', _('Geschlecht')),
        ('letter_opening', _('Briefanrede')),
        ('birthday', _('Geburtstag')),
        ('status', _('Status')),
        ('phone_priv', _('Telefon Privat')),
        ('phone_busi', _('Telefon Geschäftlich')),
        ('phone_mobi', _('Mobil')),
    ]


class ExportForm(forms.Form):
    """Docstring"""
    columns = forms.MultipleChoiceField(
        choices=member_fields, label=_("Spalten"))

class SMSAnswerForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea)

class SMSForm(forms.Form):
    """Docstring"""

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(SMSForm, self).__init__(*args, **kwargs)
        if not user.is_superuser:
            self.fields['group'].queryset = user.groups.filter()

    group = forms.ModelChoiceField(
        queryset=Group.objects.all(), label=_("Gruppe"))
    body = forms.CharField(widget=forms.Textarea,
                           max_length=500, label=_("Inhalt"))


class LatexLetterForm(forms.Form):
    """Docstring"""

    def __init__(self, *args, **kwargs):
        template = kwargs.pop('template')
        super(LatexLetterForm, self).__init__(*args, **kwargs)
        self.template = template
        for template_field in template.fields.all():
            self.fields[template_field.var_name] = eval(
                template_field.src_string())
            self.fields[template_field.var_name].label = template_field.label


class PortalFormForm(forms.Form):
    """Docstring"""

    def __init__(self, *args, **kwargs):
        portalform = kwargs.pop('portalform')
        answer = kwargs.pop('answer', None)
        super(PortalFormForm, self).__init__(*args, **kwargs)
        self.portalform = portalform
        for form_field in portalform.fields.all():
            self.fields[form_field.var_name] = form_field.get_instance()
        if portalform.editable and answer:
            self.fields['confirm_answer'] = forms.BooleanField(label=_("Antwort besätigt"),
                                                               required=False, initial=answer.confirmed)
            self.fields[portalform.email_field_name] = forms.EmailField(
                required=False,
                label=portalform.fields.get(
                    var_name=portalform.email_field_name).label,
                initial=answer.member.email,
                disabled=True
            )


class EMailFormMG(forms.Form):
    """Docstring"""

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(EMailFormMG, self).__init__(*args, **kwargs)
        if not user.is_superuser:
            self.fields['group'].queryset = user.groups.all()

    group = forms.ModelChoiceField(
        queryset=Group.objects.all(), label=_("Gruppe"))
    name = forms.CharField(label=_("Von (Name)"), max_length=50)
    sender = forms.EmailField(label=_("Von (Email)"))
    tag = forms.CharField(max_length=100, label=_("Tag"))
    subject = forms.CharField(max_length=100, label=_("Betreff"))
    img_url = forms.URLField(required=False, label=_("Header"))
    remove_points = forms.IntegerField(label=_("Punktabzug"))
    open_points = forms.IntegerField(label=_("Öffnungspunkte"))
    click_points = forms.IntegerField(label=_("Klickpunkte"))
    message = forms.CharField(widget=TinyMCE())
    template = forms.ModelChoiceField(
        queryset=MailTemplate.objects.all(), label=_("Template"))
    attachement = MultiFileField(min_num=1, max_num=6, max_file_size=1024**3*5, required=False,
                                 label="Anhänge")
