import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from Channel import routing
from Channel.middleware import JWTAuthMiddleware, ProtocolAcceptMiddleware



os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'airestaurant.settings')



application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": ProtocolAcceptMiddleware(
        JWTAuthMiddleware(
            AuthMiddlewareStack(
                URLRouter(routing.websocket_urlpatterns)
            )
        )
    ),
})
