from rest_framework import serializers
from .models import TrafficCamera, TrafficHistory

class TrafficHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficHistory
        fields = ['timestamp', 'density_pce', 'vehicle_count', 'traffic_level']

class TrafficCameraSerializer(serializers.ModelSerializer):
    history = TrafficHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = TrafficCamera
        fields = '__all__'
