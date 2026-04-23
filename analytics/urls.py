from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrafficCameraViewSet, camera_list, camera_detail, index, live_map, demo_upload, demo_result, get_progress

router = DefaultRouter()
router.register(r'cameras', TrafficCameraViewSet)

urlpatterns = [
    path('', index, name='index'), 
    path('list/', camera_list, name='camera_list'), 
    path('map/', live_map, name='live_map'),
    path('camera/<int:pk>/', camera_detail, name='camera_detail'),
    path('demo/upload/', demo_upload, name='demo_upload'),
    path('demo/progress/<int:pk>/', get_progress, name='get_progress'),
    path('demo/result/<int:pk>/', demo_result, name='demo_result'),
    path('api/', include(router.urls)),
]
