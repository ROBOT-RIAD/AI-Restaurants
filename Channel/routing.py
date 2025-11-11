from django.urls import re_path
from . import consumers


websocket_urlpatterns = [
    re_path(r'ws/alldatalive/(?P<restaurant_id>\d+)/$', consumers.RestaurantConsumer.as_asgi()),   
]