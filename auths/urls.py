from django.urls import path, include

app_name = 'auths'

urlpatterns = [
    path('api/', include('auths.api.urls')),
]