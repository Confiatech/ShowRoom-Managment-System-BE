from django.urls import path, include
from rest_framework.routers import DefaultRouter

from auths.api.views import LoginAPIView, UserViewSet
from show_room.api.views import CarViewSet, CarExpenseViewSet, CarExpenseImageViewSet, DashboardStatsAPIView

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'cars', CarViewSet, basename="cars")
router.register(r'car-expenses', CarExpenseViewSet, basename="car-expenses")
router.register(r'expense-images', CarExpenseImageViewSet, basename="expense-images")


urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('dashboard/stats/', DashboardStatsAPIView.as_view(), name='dashboard-stats'),
    path('', include(router.urls)),
]