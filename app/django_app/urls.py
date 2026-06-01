"""django_app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from webhook.views import webhook
from google_helper.views import google_hook
from telegram_helper.views import telegram_hook
from whatsapp_helper.views import whatsapp_hook
from misc.views import misc_handler

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhook', webhook),
    path('google', google_hook),
    path('telegram', telegram_hook),
    path('whatsapp', whatsapp_hook),
    path('misc', misc_handler),
]
