from django.urls import re_path
from .consumers import *


websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<public_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    re_path(r"^ws/track/delivery/(?P<delivery_id>\d+)/$", DeliveryTrackingConsumer.as_asgi()),
]