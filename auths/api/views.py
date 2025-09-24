from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from .serializers import (
    LoginSerializer,
    UserSerializer,
)

User = get_user_model()


class LoginAPIView(APIView):
    """
    Login API endpoint that authenticates users and returns JWT tokens with user details.
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """
        Authenticate user with email and password.
        
        Expected payload:
        {
            "email": "user@example.com",
            "password": "userpassword"
        }
        
        Returns:
        - JWT access and refresh tokens
        - User profile information
        """
        # Validate input data using serializer
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get validated data
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Authenticate user
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.is_active:
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    access_token = refresh.access_token
                    
                    # Serialize user data
                    user_serializer = UserSerializer(user)
                    
                    # Prepare response data
                    response_data = {
                        'access_token': str(access_token),
                        'refresh_token': str(refresh),
                        **user_serializer.data
                    }
                    
                    return Response(response_data, status=status.HTTP_200_OK)
                else:

                    return Response('Account is deactivated', status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response('Invalid email or password', status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            return Response(f'An error occurred during login {e}', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
