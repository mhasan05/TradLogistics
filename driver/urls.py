from django.urls import path
from .views import *

urlpatterns = [
    path("vehicles/", VehicleListCreateAPIView.as_view(), name="vehicle-list-create"),
    path("vehicles/<int:pk>/", VehicleDetailAPIView.as_view(), name="vehicle-detail"),
    path("documents/", DriverDocumentAPIView.as_view(), name="driver-documents"),
    path("admin/drivers/<int:driver_id>/document-status/", AdminDriverDocumentStatusAPIView.as_view(), name="update-document-status"),
]
