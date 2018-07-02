"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.conf import settings
from django.views.generic import RedirectView
from django.conf.urls.static import static 
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views
import mportal.views


urlpatterns = i18n_patterns(
    url(r'^', admin.site.urls),
    url(r'^mportal/', include('mportal.urls')),
    url(r'^advanced_filters/', include('advanced_filters.urls')),
    url(
        r'^password_reset/$',
        auth_views.PasswordResetView.as_view(),
        name='admin_password_reset',
    ),
    url(
        r'^password_reset/done/$',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done',
    ),
    url(
        r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    url(
        r'^reset/done/$',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete',
    ),

)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

urlpatterns += [
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^tinymce/', include('tinymce.urls')),
    url(r'^sms/', mportal.views.incoming_sms, name="twilio-incoming"),

]
