# coding=utf-8
"""    This file is part of MPortal.

    MPortal is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    MPortal is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with MPortal. If not, see <http://www.gnu.org/licenses/>."""
import math
from datetime import datetime

import adminactions.actions as actions
from advanced_filters.admin import AdminAdvancedFiltersMixin

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from reversion.admin import VersionAdmin

from mportal.models import Member, \
    TemplateField, LetterTemplate, SMSSender,\
    MailGunUser, MailGunEvent, MailGunMessage,\
    Skill, Occupation, Membership, CustomGroup,\
    FormField, PortalForm, PortalFormAnswer, FormFieldAnswer,\
    MemberField, ContactList, ImportMapping, FieldMapping, \
    MailTemplate, SMS, Note, Member2Member


# Register your models here.

class GroupListFilter(admin.SimpleListFilter):
    """Group List Filter"""

    title = _("Gruppen")
    parameter_name = "groups"

    def lookups(self, request, model_admin):
        groups = Group.objects.filter(user=request.user).order_by('name')
        if request.user.is_superuser:
            groups = Group.objects.all().order_by('name')
        for group in groups:
            yield (group.pk, group.name)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(position=Group.objects.get(pk=self.value()))
        return queryset

class NoteInline(admin.TabularInline):
    model = Note
    extra = 1
    fields = ["subject", "content", "created", "updated"]
    readonly_fields = ["created", "updated"]

class Member2MemberInline(admin.TabularInline):
    model = Member2Member
    fk_name = 'member_from'
    readonly_fields = ['created', 'updated']
    extra = 1

class MemberFromMemberInline(admin.TabularInline):
    model = Member2Member
    fk_name = 'member_to'
    readonly_fields = ['member_from', 'relation_name', 'created', 'updated']
    extra = 0

@admin.register(Member)
class MemberAdmin(AdminAdvancedFiltersMixin, VersionAdmin):
    list_display = ('first_name', 'last_name', 'street', 'plz', 'city',
                    'email', 'get_mobile', 'birthday',
                    'mail_activity', 'conversation_link')
    list_filter = ('status', 'skills', 'occupations',
                   'memberships', GroupListFilter, 'last_active', 'contact_list')
    date_hierarchy = 'last_active'
    filter_horizontal = ('position', 'skills', 'occupations', 'memberships')
    search_fields = ('first_name', 'last_name', 'email',
                     'city', 'phone_priv', 'phone_busi', 'phone_mobi')
    readonly_fields = ['om_number',
                       'updated', 'mail_activity', 'imported_by']
    exclude = ['read_mails', 'sent_mails']
    advanced_filter_fields = (
        'om_number', 'first_name', 'last_name', 'plz', 'city', 'country',
        'phone_priv', 'phone_busi', 'phone_mobi', 'email', 'gender',
        ('position__name', _("Gruppen")), 'birthday', 'status',
        ('skills__name', _("Fähigkeiten")),
        ('occupations__name', _("Beschäftigung")),
        ('skills__description', _("Fähigkeiten (Beschreibung)")),
        ('occupations__description', _("Beschäftigung (Beschreibung)")),
        ('memberships__name', _("Mitgliedschaften")), 'last_active',
        'activity_points', 'mail_activity'
    )

    actions = ['send_mail', 'send_mail_mg', 'send_sms', 'send_letter',
               'vcard', 'export_excel', 'activate']

    change_list_template = "mportal/change_member_list.html"
    inlines = [NoteInline, Member2MemberInline, MemberFromMemberInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super(MemberAdmin, self).get_form(request, obj=obj, **kwargs)

        def init_func(self, data=None, files=None, **kwargs):
            super(form, self).__init__(data=data, files=files, **kwargs)
            self.fields['position'].queryset = request.user.groups.all()
            self.fields['contact_list'].queryset = ContactList.objects.filter(
                users=request.user)
            if hasattr(kwargs, "instance"):
                if not kwargs['instance'].contact_list \
                        in ContactList.objects.filter(users=request.user):
                    self.fields['contact_list'].queryset = ContactList.objects\
                        .filter(pk=kwargs['instance'].contact_list.pk)
            if request.user.is_superuser:
                self.fields['position'].queryset = Group.objects.all()
                contact_list = ContactList.objects.all()
                self.fields['contact_list'].queryset = contact_list

        form.__init__ = init_func
        return form

    def get_queryset(self, request):
        qs = super(MemberAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs.order_by('last_name', 'last_name')
        groups = request.user.groups.all()
        return qs.filter(Q(position__in=groups) |
                         Q(imported_by=request.user)).distinct()

    def activate(self, request, queryset):
        queryset.update(last_active=datetime.now())
        ct = ContentType.objects.get_for_model(queryset.model)
        for obj in queryset:
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ct.pk,
                object_id=obj.pk,
                object_repr=obj.full_name,
                action_flag=CHANGE,
                change_message="Aktiv gesetzt")
    activate.short_description = _("Aktivität aktualisieren")

    def vcard(self, request, queryset):
        response = HttpResponse(content_type='text/vcard')
        for m in queryset:
            response.write('BEGIN:VCARD\n')
            response.write('VERSION:4.0\n')
            response.write('N:{m.last_name};{m.first_name};;;\n'.format(m=m))
            response.write('FN:{m.first_name} {m.last_name}\n'.format(m=m))
            if m.email.strip() != '':
                response.write('EMAIL:{m.email}\n'.format(m=m))
            if m.phone_busi.strip() != '':
                response.write(
                    'TEL;TYPE=work,voice;tel:{m.phone_busi}\n'.format(m=m))
            if m.phone_priv.strip() != '':
                response.write(
                    'TEL;TYPE=home,voice;tel:{m.phone_priv}\n'.format(m=m))
            if m.phone_mobi.strip() != '':
                response.write(
                    'TEL;TYPE=cell;tel:{m.phone_mobi}\n'.format(m=m))
            if m.birthday:
                response.write('BDAY:{m}\n'.format(m=m.birthday.strftime("%Y%m%d")))
            if m.street.strip() != '':
                response.write(
                    'ADR;TYPE=home:;;{m.street};{m.city};;{m.plz};\n'.format(m=m))
            response.write('KIND:individual\n')
            org_string = ';'.join([g.name for g in m.position.all()
                                   if g in request.user.groups.all()])
            response.write('ORG:{}\n'.format(org_string))
            response.write('UID:{m.pk}\n'.format(m=m))
            response.write("END:VCARD\n")
        response['Content-Disposition'] = \
            'attachment; filename="sektionsportal.vcf"'

        return response

    vcard.short_description = _("vCards herunterladen")

    def send_mail(self, request, queryset):
        selected = [str(m.pk) for m in queryset.all()]
        request.session['recipients'] = ','.join(selected)
        return HttpResponseRedirect(reverse('send-mail'))
    send_mail.short_description = _("E-Mail verfassen")

    def send_mail_mg(self, request, queryset):
        selected = [str(m.pk) for m in queryset.all()]
        request.session['recipients'] = ','.join(selected)
        return HttpResponseRedirect(reverse('send-mail-mg'))
    send_mail_mg.short_description = _("E-Mail verfassen (Mailgun)")

    def export_excel(self, request, queryset):
        selected = [str(m.pk) for m in queryset.all()]
        request.session['recipients'] = ','.join(selected)
        return HttpResponseRedirect(reverse('export-excel'))
    export_excel.short_description = _("Excel exportieren")

    def send_letter(self, request, queryset):
        selected = [str(m.pk) for m in queryset.all()]
        request.session['recipients'] = ','.join(selected)
        return HttpResponseRedirect(reverse('chose-template', args=(1, )))

    send_letter.short_description = _("Brief generieren")

    def send_sms(self, request, queryset):
        selected = [str(m.pk) for m in queryset.all()]
        request.session['recipients'] = ','.join(selected)
        return HttpResponseRedirect(reverse('send-sms'))

    send_sms.short_description = _("SMS verfassen")


    def save_model(self, request, obj, form, change):
        obj.user = request.user
        if not hasattr(obj, '_old_instance'):
            return super(MemberAdmin, self)\
                    .save_model(request, obj, form, change)
        if not hasattr(obj.contact_list, 'email'):
            return super(MemberAdmin, self)\
                    .save_model(request, obj, form, change)

        # Get changed fields
        changed_fields = []
        for f in Member._meta.fields:
            if f.name in obj._old_instance and\
                    obj._old_instance[f.name] != getattr(obj, f.name):
                if not getattr(obj, f.name) and not obj._old_instance[f.name]:
                    continue
                changed_fields.append((f.name, getattr(obj, f.name)))

        if changed_fields:
            mail_body = ("Mitglied {obj.full_name} ({obj.om_number}) " +\
                        "wurde vom Benutzer {request.user} aktualisiert," +\
                        "\n\nÄnderungen:\n").format(obj=obj, request=request)
            for k, v in changed_fields:
                if k == "birthday":
                    field_name = "Geburtsdatum"
                else:
                    field_name = k
                    mail_body += "{}:\t{}\n".format(field_name, v if v else '<gelöscht>')
            print("Sending mail!")
            send_mail(
                'Sektionsportal: {obj.om_number} aktualisert'.format(obj=obj),
                mail_body,
                'info@portal.juso.ch',
                [obj.contact_list.email],
                fail_silently=False
            )
            print("Mail sent!")
        print(obj, form, change)
        super(MemberAdmin, self).save_model(request, obj, form, change)


@admin.register(MailGunUser)
class MailGunUserAdmin(VersionAdmin):
    list_display = ['domain', 'group']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        groups = request.user.groups.all()
        return qs.filter(group__in=groups).distinct()


@admin.register(SMSSender)
class SMSSenderAdmin(VersionAdmin):
    list_display = ('group', 'username', 'sid', 'saldo')
    list_display_links = ('username', )
    actions = ['reset']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        groups = request.user.groups.all()
        return qs.filter(group__in=groups).distinct()

    def reset(self, request, queryset):
        now = datetime.now()
        queryset.update(reset=now)


class MailGunEventInline(admin.TabularInline):
    model = MailGunEvent
    extra = 1
    readonly_fields = ['timestamp', 'recipient', 'event', 'country',
                       'client_type', 'device_type', 'url']
    fieldsets = (
        (
            None,
            {
                'fields': ('event', 'recipient', 'timestamp', 'country',
                           'client_type', 'device_type', 'url', )
            }
        ),
    )


@admin.register(MailGunMessage)
class MailGunMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'report_link', 'created',
                    'group', 'sender', 'tag', 'opening_rate')
    list_filter = ('tag', )
    search_fields = ('subject', 'sender', 'tag', 'group')
    date_hierarchy = 'created'
    readonly_fields = ['recipient_count', 'opening_rate',
                       'recipients', 'subject', 'content',
                       'sender', 'group']

    fieldsets = (
        (
            None,
            {
                'fields': ('group', 'subject', 'sender',
                           'content', 'recipients',
                           'open_points', 'click_points',
                           'remove_points', 'recipient_count', 'opening_rate')
            }
        ),
    )

    inlines = [
        MailGunEventInline,
    ]

    def opening_rate(self, i):
        if i.recipients.count():
            return '{:.0f}'.format(i.read_count()/i.recipients.count()*100)
        return '---'

    opening_rate.short_description = _("Öffnungsrate")

    def get_queryset(self, request):
        qs = super(MailGunMessageAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        groups = request.user.groups.all()
        return qs.filter(group__in=groups).distinct()

    def has_add_permission(self, request):
        return False


@admin.register(MailGunEvent)
class MailGunEventAdmin(admin.ModelAdmin):
    list_display = ('event', 'recipient', 'subject',
                    'country', 'tag', 'timestamp')
    list_filter = ('tag', 'event')
    date_hierarchy = 'timestamp'
    readonly_fields = ('event', 'recipient', 'subject', 'country',
                       'tag', 'timestamp', 'url', 'message',
                       'device_type', 'client_type', 'client_os',)

    def get_queryset(self, request):
        qs = super(MailGunEventAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        groups = request.user.groups.all()
        return qs.filter(message__group__in=groups).distinct()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TemplateFieldInline(admin.TabularInline):
    model = TemplateField
    extra = 3
    ordering = ['ordering', 'var_name']


@admin.register(LetterTemplate)
class TemplateAdmin(VersionAdmin):
    list_display = ['name']
    inlines = [
        TemplateFieldInline,
    ]


class UserInline(admin.TabularInline):
    model = CustomGroup.user_set.through

    def has_change_permission(self, request, obj=None):
        # returning false causes table to not show up in admin page :-(
        # I guess we have to allow changing for now
        if not obj:
            return True
        if obj in request.user.groups.all():
            return True
        return False


@admin.register(CustomGroup)
class GroupAdmin(VersionAdmin):
    list_display = ['name']
    fields = ['name']
    inlines = [UserInline]

    def get_queryset(self, request):
        qs = super(GroupAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(Skill)
class SkillAdmin(VersionAdmin):
    list_display = ['name', 'description']


@admin.register(Occupation)
class OccupationAdmin(VersionAdmin):
    list_display = ['name', 'description']


@admin.register(Membership)
class MembershipAdmin(VersionAdmin):
    list_display = ['name', 'description']


class FormFieldInline(admin.StackedInline):
    model = FormField
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('var_name', 'label', 'input_type', 'required')
        }),
        ('Erweitert', {
            'classes': ('collapse',),
            'fields': ('initial', 'ordering', 'choices', 'widget')
        })
    )


class AnswerFieldInline(admin.TabularInline):
    model = FormFieldAnswer
    extra = 0


class MemberFieldInline(admin.TabularInline):
    model = MemberField


class FieldMappingInline(admin.TabularInline):
    model = FieldMapping
    extra = 6


@admin.register(ImportMapping)
class ImportMappingAdmin(VersionAdmin):
    list_display = ['name']
    inlines = [FieldMappingInline]


@admin.register(MailTemplate)
class MailTemplateAdmin(VersionAdmin):
    list_display = ['name']


@admin.register(PortalForm)
class PortalFormAdmin(VersionAdmin):
    inlines = [FormFieldInline, MemberFieldInline]
    list_display = ['name', 'slug', 'result_link', 'public_link',
                    'contact_name', 'contact_mail', 'answer_count']
    filter_vertical = ['users', 'allowed_groups']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(users=request.user)


@admin.register(ContactList)
class ContactListAdmin(VersionAdmin):
    list_display = ['name']
    filter_vertical = ['users']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(users=request.user)


@admin.register(PortalFormAnswer)
class PortalFormAnswerAdmin(admin.ModelAdmin):
    list_display = ['form_name', 'member_name']
    inlines = [AnswerFieldInline]

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(confirmed=True)
        if request.user.is_superuser:
            return qs
        return qs.filter(portal_form__users=request.user)

@admin.register(SMS)
class SMSAdmin(admin.ModelAdmin):
    list_display = ['time', 'member','account', 'content', 'incoming', 'open_conversation']
    list_filter = ['incoming', 'twilio_account']
    search_fields = ['content', 'member__first_name']
    readonly_fields = ['time', 'member', 'content', 'incoming', 'time', 'twilio_account', 'is_mass',
            'twilio_sid', 'location_string']


    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        accounts = SMSSender.objects.filter(group__in=request.user.groups.all())
        return qs.filter(twilio_account__in=accounts)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # returning false causes table to not show up in admin page :-(
        # I guess we have to allow changing for now
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class LogAdmin(admin.ModelAdmin):
    """Create an admin view of the history/log table"""
    list_display = ('action_time', 'user', 'content_type',
                    'change_message', 'is_addition',
                    'is_change', 'is_deletion')
    list_filter = ['action_time', 'user', 'content_type']
    ordering = ('-action_time',)
    # We don't want people changing this historical record:

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # returning false causes table to not show up in admin page :-(
        # I guess we have to allow changing for now
        return True

    def has_delete_permission(self, request, obj=None):
        return False


old_app_list = admin.site.get_app_list


def get_app_list_hack(request):
    new_list = []
    old_list = old_app_list(request)
    for app in old_list:
        if app['app_label'] == 'mportal':
            app['models'].sort(
                key=lambda model: ' ' if model['object_name'] == 'Member'
                else model['object_name'])
            new_list.append(app)
            old_list.remove(app)
    new_list += old_list
    return new_list


admin.site.get_app_list = get_app_list_hack
actions.add_to_site(admin.site)
