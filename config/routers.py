from django.urls import path, include
from rest_framework.routers import DefaultRouter

from auths.api.views import LoginAPIView, UserViewSet


# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')


urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('', include(router.urls)),
]