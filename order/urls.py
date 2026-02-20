from django.urls import path
from .views import *

urlpatterns = [
    # Customer/Business
    path("deliveries/", DeliveryListCreateAPIView.as_view(), name="delivery-list-create"),
    path("deliveries/<int:pk>/", DeliveryDetailAPIView.as_view(), name="delivery-detail"),
    path("deliveries/<int:pk>/search-driver/", DeliveryStartSearchingAPIView.as_view(), name="delivery-search-driver"),
    path("deliveries/<int:pk>/cancel/", DeliveryCancelAPIView.as_view(), name="delivery-cancel"),
    path("deliveries/<int:pk>/rate/", DeliveryRateAPIView.as_view(), name="delivery-rate"),
    path("deliveries/<int:pk>/tip/", DeliveryTipAPIView.as_view(), name="delivery-tip"),

    # Driver
    path("driver/deliveries/available/", DriverAvailableDeliveriesAPIView.as_view(), name="driver-available"),
    path("driver/deliveries/<int:pk>/accept/", DriverAcceptDeliveryAPIView.as_view(), name="driver-accept"),
    path("driver/deliveries/<int:pk>/status/", DriverUpdateDeliveryStatusAPIView.as_view(), name="driver-status"),
]