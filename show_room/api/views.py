from rest_framework import viewsets, permissions
from show_room.models import Car
from .serializers import CarSerializer


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all().prefetch_related("investments__investor")
    serializer_class = CarSerializer
    permission_classes = [permissions.IsAuthenticated]
