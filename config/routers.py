from django.urls import path, include
from rest_framework.routers import DefaultRouter

from auths.api.views import LoginAPIView, UserViewSet
from show_room.api.views import CarViewSet, CarExpenseViewSet

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'cars', CarViewSet, basename="cars")
router.register(r'car-expenses', CarExpenseViewSet, basename="car-expenses")


urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('', include(router.urls)),
]