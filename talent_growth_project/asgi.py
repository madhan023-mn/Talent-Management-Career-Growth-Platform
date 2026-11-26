"""
ASGI config for Talent Growth Platform.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_growth_project.settings')

application = get_asgi_application()
app = application
