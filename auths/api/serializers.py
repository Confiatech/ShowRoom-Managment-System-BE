from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login request data.
    """
    email = serializers.EmailField(
        required=True,
        help_text="User's email address"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User's password"
    )

    def validate_email(self, value):
        """
        Validate email format and normalize it.
        """
        return value.lower().strip()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data in responses.
    """
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'address',
            'cnic'
        ]
        read_only_fields = ['id']

