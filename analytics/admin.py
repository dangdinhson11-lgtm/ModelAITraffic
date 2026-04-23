from django.contrib import admin
from .models import TrafficCamera, TrafficHistory

@admin.register(TrafficCamera)
class TrafficCameraAdmin(admin.ModelAdmin):
    list_display = ('title', 'current_density', 'current_traffic_level', 'last_updated')
    search_fields = ('title',)

@admin.register(TrafficHistory)
class TrafficHistoryAdmin(admin.ModelAdmin):
    list_display = ('camera', 'timestamp', 'density_pce', 'vehicle_count', 'traffic_level')
    list_filter = ('traffic_level', 'camera')
