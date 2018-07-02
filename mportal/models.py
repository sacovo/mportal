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
import datetime

from collections import namedtuple

from colorfield.fields import ColorField

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.utils.html import mark_safe
from django.urls import reverse

import textwrap
from twilio.rest import Client


class CustomGroup(Group):
    class Meta:
        verbose_name = _("Gruppe")
        verbose_name_plural = _("Gruppen")
        ordering = ['name']


class ContactList(models.Model):
    name = models.CharField(max_length=150)
    users = models.ManyToManyField(User)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name = _("Kontaktliste")
        verbose_name_plural = _("Kontaktlisten")
        ordering = ['name']

    def __str__(self):
        return self.name


field_choices = (
    ('om_number', _("OM Nummer")),
    ('first_name', _("Vorname")),
    ('last_name', _("Nachname")),
    ('street', _("Strasse")),
    ('plz', _("PLZ")),
    ('city', _("Ort")),
    ('phone_priv', _("Telefon privat")),
    ('phone_busi', _("Telefon Geschäftlich")),
    ('phone_mobi', _("Mobil")),
    ('country', _("Land")),
    ('email', _("E-Mail")),
    ('gender', _('Geschlecht')),
    ('letter_opening', _("Briefanrede")),
    ('birthday', _("Geburtstag")),
    ('position', _("Gruppen")),
    ('birthday_day', _("Geburtstag Tag")),
    ('birthday_month', _("Geburtstag Monat")),
    ('birthday_year', _("Geburtstag Year")),
)


class ImportMapping(models.Model):
    name = models.CharField(max_length=100)

    def birthday_single(self):
        return self.fields.filter(var_name="birthday").exists()

    def birthday_multiple(self):
        if not self.fields.filter(var_name="birthday_day").exists():
            return False
        if not self.fields.filter(var_name="birthday_month").exists():
            return False
        if not self.fields.filter(var_name="birthday_year").exists():
            return False
        return True

    def birthday_col_names(self):
        return [
            self.fields.get(var_name="birthday_day").column_name,
            self.fields.get(var_name="birthday_month").column_name,
            self.fields.get(var_name="birthday_year").column_name,
        ]

    class Meta:
        verbose_name = _("Verknüpfung")
        verbose_name_plural = _("Verknüpfungen")
        ordering = ['name']

    def __str__(self):
        return self.name


class FieldMapping(models.Model):
    var_name = models.CharField(max_length=100, choices=field_choices)
    column_name = models.CharField(max_length=100)
    mapping = models.ForeignKey(
        ImportMapping, related_name="fields", on_delete=models.CASCADE)

    def __str__(self):
        return '{self.column_name} -> {self.var_name}'.format(self=self)


# Create your models here.
class Membership(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=150)
    description = models.TextField(verbose_name=_("Beschreibung"), blank=True)

    class Meta:
        verbose_name = _("Mitgliedschaft")
        verbose_name_plural = _("Mitgliedschaften")
        ordering = ['name']

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=150)
    description = models.TextField(verbose_name=_("Beschreibung"), blank=True)

    class Meta:
        verbose_name = _("Fähigkeit")
        verbose_name_plural = _("Fähigkeiten")
        ordering = ['name']

    def __str__(self):
        return self.name


class Occupation(models.Model):
    name = models.CharField(verbose_name=_("Name"), max_length=150)
    description = models.TextField(verbose_name=_("Beschreibung"), blank=True)

    class Meta:
        verbose_name = _("Beschäftigung")
        verbose_name_plural = _("Beschäftigungen")
        ordering = ['name']

    def __str__(self):
        return self.name


class Member(models.Model):
    """Member class"""
    SYMPI = 'SY'
    MEMBER = 'ME'
    ELSE = 'EL'
    STATUS_CHOICES = (
        (SYMPI, _("Sympi")),
        (MEMBER, _("Mitglied")),
        (ELSE, _("Sonstige")),
    )

    om_number = models.CharField(verbose_name=_(
        "OM-Nummer"), blank=True, max_length=120)
    anrede = models.CharField(
        max_length=30, verbose_name=_("Anrede"), blank=True)
    first_name = models.CharField(
        max_length=30, verbose_name=_("Vorname"), blank=True)
    last_name = models.CharField(
        max_length=30, verbose_name=_("Name"), blank=True)
    street = models.CharField(
        max_length=50, verbose_name=_("Strasse"), blank=True)
    plz = models.CharField(max_length=10, verbose_name=_("PLZ"), blank=True)
    city = models.CharField(max_length=80, verbose_name=_("Ort"), blank=True)
    country = models.CharField(
        max_length=2, verbose_name=_("Land"), blank=True)
    phone_priv = models.CharField(
        max_length=30, blank=True, verbose_name=_("Telefon Privat"))
    phone_busi = models.CharField(
        max_length=30, blank=True, verbose_name=_("Telefon Geschäftlich"))
    phone_mobi = models.CharField(
        max_length=30, blank=True, verbose_name=_("Mobil"))
    email = models.EmailField(blank=True, verbose_name=_("E-Mail"))
    gender = models.CharField(
        max_length=20, blank=True, verbose_name=_("Geschlecht"))
    letter_opening = models.CharField(
        max_length=40, verbose_name=_("Briefanrede"), blank=True)
    birthday = models.DateField(
        verbose_name="Geburtstag", null=True, blank=True)
    status = models.CharField(max_length=40, verbose_name=_("Status"), null=True,
                              choices=STATUS_CHOICES, default=ELSE)
    updated = models.BooleanField(default=True)
    position = models.ManyToManyField(
        Group, blank=True, verbose_name=_("Gruppen"))
    skills = models.ManyToManyField(
        Skill, blank=True, verbose_name=_("Fähigkeiten"))
    occupations = models.ManyToManyField(
        Occupation, blank=True, verbose_name=_("Veranstaltungen"))
    memberships = models.ManyToManyField(
        Membership, blank=True, verbose_name=_("Mitgliedschaften"))
    last_active = models.DateTimeField(verbose_name=_("Letzte Aktivität"),
                                       default=datetime.datetime.fromtimestamp(0))
    activity_points = models.IntegerField(default=0)
    read_mails = models.ManyToManyField("MailGunMessage", blank=True)
    sent_mails = models.IntegerField(default=0)
    mail_activity = models.IntegerField(
        default=0, verbose_name=_("Mail Aktivität"))
    contact_list = models.ForeignKey(
        ContactList, null=True, blank=True, on_delete=models.CASCADE)
    imported_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE)
    related_to = models.ManyToManyField("self",symmetrical=False,
            through="Member2Member",verbose_name=_("Beziehung"))

    def section(self):
        if self.position.count() > 0:
            return self.position.all()[0]
        return ''

    section.short_description = _("Sektion")

    def conversation_link(self):
        url = reverse('chose-sender', kwargs={'member': self.pk})
        return mark_safe('<a href="{}">SMS</a>'.format(url))

    conversation_link.short_description = ' '

    def occupation(self):
        if self.occupations.count() > 0:
            return self.occupations.all()[0]
        return ''

    occupation.short_description = _("Veranstaltungen")

    def get_absolute_url(self):
        return reverse('admin:mportal_member_change', args=(self.pk,))

    @classmethod
    def from_db(cls, db, field_names, values):
        """Caches old values"""
        new = super(Member, cls).from_db(db, field_names, values)
        new._old_instance = {k: v for k, v in zip(field_names, values)}
        return new

    def activate(self):
        self.last_active = datetime.datetime.now()
        self.save()

    @property
    def get_mobile(self):
        """Get a mobile 07* number"""
        if self.phone_priv.startswith('07'):
            return self.phone_priv
        if self.phone_busi.startswith('07'):
            return self.phone_busi
        if self.phone_mobi.startswith('07'):
            return self.phone_mobi
        return None

    def get_positions(self):
        """Get all groups as a string"""
        return ', '.join([position.name for position in self.position.all()])
    get_positions.short_description = _("Gruppen")
    get_positions.allow_tags = True

    @property
    def full_name(self):
        """Return the first name and the second name"""
        return self.first_name + " " + self.last_name

    @staticmethod
    def fields_to_ignore():
        """Return the fields not in the excel"""
        return {'updated',
                'anrede', '_old_instance',
                '_state', '_prefetched_objects_cache', 'pk', 'contact_list_id',
                'last_active', 'activity_points', 'sent_mails', 'mail_activity',
                'imported_by_id', 'imported_by'}

    @staticmethod
    def as_named_tuple():
        """Return all fields as a named tuple"""
        return namedtuple('Member', ' '.join(
            ['position'] + [m.name for m in Member._meta.fields
                            if m.name not in Member.fields_to_ignore()]))

    @staticmethod
    def get_all_as_named_tuple(contact_list):
        """Get all members as named tuple"""
        result = set()
        tuple_cls = Member.as_named_tuple()
        for member in Member.objects.filter(contact_list=contact_list).prefetch_related('position'):
            positions = frozenset({p.name for p in member.position.all()})

            for f in Member.fields_to_ignore():
                try:
                    del member.__dict__[f]
                except:
                    pass
            result.add(
                tuple_cls(positions, contact_list=contact_list, **member.__dict__))
        return result

    def __str__(self):
        return self.full_name

    def age(self):
        if self.birthday:
            return datetime.date.today().year - self.birthday.year
        return ''

    class Meta:
        ordering = ['last_name', 'last_name']
        verbose_name = _("Mitglied")
        verbose_name_plural = _("Mitglieder")
        indexes = [
            models.Index(fields=['om_number', 'contact_list']),
        ]


class Member2Member(models.Model):
    member_from = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="from_relation",\
            verbose_name="Relation von")
    member_to = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="to_relation", \
            verbose_name="Relation zu")
    relation_name = models.CharField(max_length=100, verbose_name="Relation")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.relation_name

    class Meta:
        verbose_name = "M2M"
        verbose_name_plural = "M2M"


@receiver(pre_delete, sender=Member)
def send_deletion_mail(sender, instance, using, **kwargs):
    if hasattr(instance.contact_list, 'email'):
        mail_body = ("Mitglied {obj.full_name} ({obj.om_number}) wurde " +\
                     "gelöscht.\n").format(obj=instance)
        send_mail(
            'MPortal: {obj.om_number} gelöscht'.format(obj=instance),
            mail_body,
            settings['DEFAULT_FROM_EMAIL'],
            [instance.contact_list.email],
            fail_silently=False
        )


SEXES = (
    ('m', 'male'),
    ('f', 'female'),
    ('o', 'other'),
)


INPUT_TYPES = (
    ('forms.DateField', _('Datum')),
    ('forms.TimeField', _('Zeit')),
    ('forms.CharField', _('Text')),
    ('forms.BooleanField', _('Wahrheitswert')),
    ('forms.DecimalField', _('Zahl')),
    ('forms.EmailField', _('E-Mail')),
    ('forms.URLField', _('URL')),
    ('forms.FileField', _('Datei')),
)


class TemplateField(models.Model):
    """TemplateField"""
    var_name = models.CharField(max_length=100)
    input_type = models.CharField(max_length=20, choices=INPUT_TYPES)
    label = models.CharField(max_length=100)
    template = models.ForeignKey(
        'LetterTemplate', related_name="fields", on_delete=models.CASCADE)
    argument_string = models.CharField(max_length=200, blank=True)
    ordering = models.IntegerField(default=1)

    def src_string(self):
        return self.input_type + '(' + self.argument_string + ')'

    class Meta:
        ordering = ['ordering', 'var_name']
        verbose_name = _("Brieffeld")
        verbose_name_plural = _("Brieffelder")


class LetterTemplate(models.Model):
    name = models.CharField(max_length=100)
    template = models.FileField(
        upload_to="templates/", verbose_name=_("Vorlage (.tex)"))

    class Meta:
        verbose_name = _("Briefvorlage")
        verbose_name_plural = _("Briefvorlagen")
        ordering = ['name']


FORM_INPUT_TYPES = (
    ('forms.DateField', _('Datum')),
    ('forms.TimeField', _('Zeit')),
    ('forms.CharField', _('Text')),
    ('forms.ChoiceField', _('Auswahl')),
    ('forms.MultipleChoiceField', _('Mehrfachauswahl')),
    ('forms.BooleanField', _('Wahrheitswert')),
    ('forms.DecimalField', _('Zahl')),
    ('forms.EmailField', _('E-Mail')),
    ('forms.URLField', _('URL')),
    ('forms.FileField', _('Datei')),
)

WIDGETS = (
    ('forms.PasswordInput', _("Passwort-Widget")),
    ('forms.Textarea', _("Langer Text")),
    ('forms.SelectInput', _("Select-Widget")),
    ('forms.Select', _("Select-Widget")),
    ('forms.SelectMultiple', _("Mehrfach-Select")),
    ('forms.RadioSelect', _("Select-Radio-Widget")),
    ('forms.CheckboxSelectMultiple', _("Multipleselect Checkbox")),
)


def get_widget(widget_str):
    from django import forms
    return eval(widget_str)


def get_field_class(input_str):
    from django import forms
    return eval(input_str)


class FormField(models.Model):
    """TemplateField"""
    var_name = models.CharField(max_length=100)
    input_type = models.CharField(max_length=50, choices=FORM_INPUT_TYPES)
    label = models.CharField(max_length=100)
    form = models.ForeignKey(
        'PortalForm', related_name="fields", on_delete=models.CASCADE)
    ordering = models.IntegerField(default=1)
    required = models.BooleanField(_("Benötigt"), default=True)
    initial = models.CharField(_("Default"), blank=True, max_length=300)
    choices = models.TextField(
        _("Auswahl"), blank=True, help_text=_("Eine Option pro Zeile"))
    widget = models.CharField(_("Widget"), blank=True,
                              choices=WIDGETS, max_length=100)

    def src_string(self):
        return self.input_type + '(' + self.argument_string + ')'

    def get_instance(self):
        kwargs = dict()
        kwargs['label'] = self.label
        kwargs['required'] = self.required
        if self.initial:
            kwargs['initial'] = self.initial
        if self.choices:
            kwargs['choices'] = ((s.strip(), s.strip())
                                 for s in self.choices.split('\n'))
        if self.widget:
            kwargs['widget'] = get_widget(self.widget)
        return get_field_class(self.input_type)(**kwargs)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['ordering', 'var_name']
        verbose_name = _("Formularfeld")
        verbose_name_plural = _("Formularfelder")


conf_text = """Hallo {member.first_name},
Du hast bei {form.name} teilgenommen. Klicke auf disen Link, um deine Antwort zu bestätigen:

{confirmation_link}

Vielen Dank und Freundliche Grüsse
XXX
"""


class PortalForm(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    allowed_groups = models.ManyToManyField(Group)
    color = ColorField(default="#4CAF50", verbose_name=_("Hintergrund"))
    destination_group = models.ForeignKey(
        Group, related_name="form_dest", null=True, blank=True, on_delete=models.CASCADE)
    email_field_name = models.CharField(max_length=300, default='email')
    confirmation_text = models.TextField(default=conf_text)
    contact_name = models.CharField(max_length=100, default="JUSO Schweiz")
    contact_mail = models.EmailField(default="info@juso.ch")
    users = models.ManyToManyField(User)
    editable = models.BooleanField(default=False, verbose_name=_("Editierbar"))

    def answer_count(self):
        return self.portalformanswer_set.count()
    answer_count.short_description = _("# Antworten")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("form-result-view", kwargs={'slug': str(self.slug)})

    def result_link(self):
        return mark_safe(
            _('<a href="{}">Resultate anzeigen</a>').format(
                self.get_absolute_url()
                )
        )
    result_link.short_description = _('Resultate')

    def public_link(self):
        url = reverse('form-view', kwargs={'slug': self.slug})
        return mark_safe(_('<a href="{}">Formular öffnen</a>').format(url))
    public_link.short_description = _('Anzeigen')

    class Meta:
        verbose_name = _("Formular")
        verbose_name_plural = _("Formulare")
        ordering = ['name']


class MemberField(models.Model):
    var_name = models.CharField(max_length=50, choices=field_choices)
    label = models.CharField(max_length=50)
    form = models.ForeignKey(PortalForm, on_delete=models.CASCADE)

    def __str__(self):
        return self.label


class PortalFormAnswer(models.Model):
    portal_form = models.ForeignKey(PortalForm, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    confirmation_string = models.CharField(max_length=200)
    confirmed = models.BooleanField(verbose_name=_("Bestätigt"))

    def __str__(self):
        return _('Formular Antwort: {self.portal_form} von {self.member}').format(self=self)

    def form_name(self):
        return self.portal_form.name

    def member_name(self):
        return self.member.full_name

    class Meta:
        verbose_name = _("Formular Antwort")
        verbose_name_plural = _("Formular Antworten")


class FormFieldAnswer(models.Model):
    form_field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    value = models.TextField()
    answer = models.ForeignKey(
        PortalFormAnswer, related_name="answers", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Formular-Antwort")
        verbose_name_plural = _("Formular-Antworten")


class SMSSender(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    username = models.CharField(max_length=100)
    sid = models.CharField(max_length=40)
    auth = models.CharField(max_length=40)

    class Meta:
        verbose_name = _("Twilio-Zugang")
        verbose_name_plural = _("Twilio-Zugänge")

    def __str__(self):
        return '{self.group}: {self.number}'.format(self=self)

    def saldo(self):
        return '0'


class MailGunUser(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    domain = models.CharField(max_length=20)
    api_key = models.CharField(max_length=100)

    class Meta:
        verbose_name = _("Mailgun-Zugang")
        verbose_name_plural = _("Mailgun-Zugänge")

    def __str__(self):
        return '{self.group}: {self.domain}'.format(self=self)


class MailGunMessage(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    sender = models.EmailField()
    content = models.TextField()
    recipients = models.ManyToManyField(Member)
    tag = models.CharField(max_length=100, blank=True, null=True)
    open_points = models.SmallIntegerField(default=0)
    click_points = models.SmallIntegerField(default=0)
    remove_points = models.SmallIntegerField(default=0)

    def recipient_count(self):
        return self.recipients.count()
    recipient_count.short_description = _("Empfänger*innen")

    class Meta:
        ordering = ['-created']
        verbose_name = _("Tracking-Mail")
        verbose_name_plural = _("Tracking-Mails")

    def read_count(self):
        return len(self.read())

    def delivered(self):
        return self.recipients.filter(
            pk__in=self.mailgunevent_set.filter(event='delivered')
            .values_list('recipient', flat=True)
        )

    def read(self):
        recipients = set(self.mailgunevent_set.filter(event='opened').
                         values_list('recipient', flat=True))
        return_list = []
        for recipient in recipients:
            ts = self.mailgunevent_set.filter(recipient=recipient).\
                order_by('timestamp')[0].timestamp
            return_list.append((self.recipients.get(pk=recipient), ts))
        return_list.sort(key=lambda t: t[1])
        return return_list

    def unread(self):
        return self.recipients.exclude(
            pk__in=self.mailgunevent_set.filter(event='opened').values_list('recipient',
                                                                            flat=True)
        )

    def not_clicked(self):
        return self.recipients.exclude(
            pk__in=self.mailgunevent_set.filter(event='clicked').values_list('recipient',
                                                                             flat=True)
        )

    def events(self, event='opened', url=None):
        if event == 'clicked':
            return self.mailgunevent_set.filter(event=event, url=url).order_by('timestamp')
        return self.mailgunevent_set.filter(event=event).order_by('timestamp')

    def unique_events(self, event='opened', url=None):
        if event == 'clicked':
            queryset = self.mailgunevent_set.filter(
                event=event, url=url).order_by('timestamp')
            u_list = []
            while queryset.count() > 0:
                event = queryset[0]
                u_list.append(event)
                queryset = queryset.exclude(recipient=event.recipient)
                return u_list
        queryset = self.mailgunevent_set.filter(
            event=event).order_by('timestamp')
        u_list = []
        while queryset.count() > 0:
            event = queryset[0]
            u_list.append(event)
            queryset = queryset.exclude(recipient=event.recipient)
            return u_list

    def urls(self):
        return list(set(self.mailgunevent_set.filter(event='clicked').values_list('url', flat=True)))

    def click_count_for(self, url):
        return self.mailgunevent_set.filter(event="clicked", url=url).count()

    def unique_click_count_for(self, url):
        return len(set(self.mailgunevent_set.filter(event="clicked", url=url).values_list('recipient')))

    def report_link(self):
        url = reverse('mailgun-report', args=(self.pk,))
        return mark_safe(_(
            '<a href="{}">Report anzeigen</a>').format(url)
        )

    def get_absolute_url(self):
        return reverse('mailgun-report', args=(self.pk,))

    def __str__(self):
        return self.subject

class Note(models.Model):
    subject = models.CharField(max_length=100, verbose_name=_("Betreff"))
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("Notiz"))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Erstellt"))
    updated = models.DateTimeField(auto_now=True, verbose_name=_("Bearbeitet"))

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = _("Notiz")
        verbose_name_plural = _("Notizen")
        ordering = ['-created']


class MailGunEvent(models.Model):
    MAILGUN_EVENTS = (
        ('accepted', 'accepted'),
        ('rejected', 'rejected'),
        ('delivered', 'delivered'),
        ('failed', 'failed'),
        ('opened', 'opened'),
        ('clicked', 'clicked'),
        ('unsubscribed', 'unsubscribed'),
        ('complained', 'complained'),
        ('stored', 'stored')
    )

    def subject(self):
        return self.message.subject

    message = models.ForeignKey(MailGunMessage, on_delete=models.CASCADE)
    event = models.CharField(max_length=30, choices=MAILGUN_EVENTS)
    recipient = models.ForeignKey(Member, on_delete=models.CASCADE)
    country = models.CharField(max_length=20, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    client_type = models.CharField(max_length=50, blank=True)
    client_os = models.CharField(max_length=50, blank=True)
    tag = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Tracking-Event: {self.event}@{self.timestamp}".format(self=self)

    class Meta:
        verbose_name = "Tracking-Event"
        verbose_name_plural = "Tracking-Events"
        ordering = ['-timestamp']



class MailTemplate(models.Model):
    name = models.CharField(max_length=180)
    template = models.FileField(
        upload_to="mail-templates/", verbose_name="Vorlage (.html)")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Mail Vorlage")
        verbose_name_plural = _("Mail Vorlagen")
        ordering = ['name']

class SMS(models.Model):
    content = models.TextField(verbose_name=_("Inhalt"))
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    incoming = models.BooleanField(verbose_name=_("Eingehend"))
    time = models.DateTimeField(auto_now_add=True)
    twilio_account = models.ForeignKey(SMSSender, on_delete=models.CASCADE)
    is_mass = models.BooleanField(default=True)
    location_string = models.CharField(max_length=300, blank=True)
    twilio_sid = models.CharField(max_length=100, blank=True)
    delivered = models.BooleanField(default=True)

    def open_conversation(self):
        url = reverse('conversation-view', kwargs={
            'sender': self.twilio_account.pk,
            'member': self.member.pk,
            })
        return mark_safe(_(
            '<a href="{}">Konversation anzeigen</a>').format(url)
        )

    def account(self):
        return self.twilio_account.group.name

    def __str__(self):
        return '{}@{:%Y-%m-%d %H:%M}'.format(self.member, self.time)
    open_conversation.short_description = ""

    def conversation(self):
        return self.member.sms_set.filter(twilio_account=self.twilio_account)

    class Meta:
        verbose_name = _("SMS")
        verbose_name_plural = _("SMS")
        ordering  = ['-time']

