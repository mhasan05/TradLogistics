from django.contrib import admin
from .models import *
from .models import Truck

admin.site.register(Company)

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        "truck_id",
        "vehicle_type",
        "operating_zone",
        "status",
        "driver",
        "owner",
        "cylinder_12kg",
        "cylinder_25kg",
        "created_at",
    )
    list_filter = ("status", "vehicle_type", "operating_zone")
    search_fields = ("truck_id", "operating_zone", "driver__phone", "owner__email")
    readonly_fields = ("public_id", "created_at", "updated_at")


