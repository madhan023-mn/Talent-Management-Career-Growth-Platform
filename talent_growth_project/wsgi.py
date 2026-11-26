"""
WSGI config for Talent Growth Platform.
Exposes the WSGI callable as a module-level variable named `application` and `app` for Vercel.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_growth_project.settings')

application = get_wsgi_application()
app = application
