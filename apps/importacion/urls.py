"""URL routes for importacion app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImportJobViewSet

router = DefaultRouter()
router.register('', ImportJobViewSet, basename='importjob')

urlpatterns = [
    path('', include(router.urls)),
]
