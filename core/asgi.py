import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()   # 🔥 VERY IMPORTANT

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from chat.routing import websocket_urlpatterns
from chat.ws_auth import JwtAuthMiddlewareStack

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JwtAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})