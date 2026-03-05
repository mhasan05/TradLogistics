from django.urls import path
from .views import *

urlpatterns = [
    # CRUD
    path("trucks/", TruckListCreateAPIView.as_view()),
    path("trucks/<uuid:public_id>/", TruckDetailAPIView.as_view()),

    path("trucks/<uuid:public_id>/location/", TruckLocationUpdateAPIView.as_view()),

    path("zones/", ZoneListCreateAPIView.as_view()),
    path("zones/<int:id>/", ZoneDetailAPIView.as_view()),

    # Assign / unassign
    path("trucks/<uuid:public_id>/assign-driver/", TruckAssignDriverAPIView.as_view()),
    path("trucks/<uuid:public_id>/unassign-driver/", TruckUnassignDriverAPIView.as_view()),

    # Inventory
    path("trucks/<uuid:public_id>/inventory/", TruckInventoryUpdateAPIView.as_view()),

    # Dashboard
    path("fleet/dashboard/", FleetDashboardAPIView.as_view()),

    path("dashboard/", CompanyDashboardAPIView.as_view(), name="company-dashboard"),
]