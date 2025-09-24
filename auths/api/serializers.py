from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

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


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users (superadmin only).
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text="User's password"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirm password"
    )

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'confirm_password',
            'first_name',
            'last_name',
            'cnic',
            'phone_number',
            'address',
            'role'
        ]

    def validate_email(self, value):
        """
        Validate email format and normalize it.
        """
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return email

    def validate(self, attrs):
        """
        Validate password confirmation.
        """
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Password and confirm password do not match.")
        return attrs

    def create(self, validated_data):
        """
        Create user with encrypted password.
        """
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user data.
    """
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text="New password (optional)"
    )

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'first_name',
            'last_name',
            'cnic',
            'phone_number',
            'address',
            'role',
            'is_active'
        ]

    def validate_email(self, value):
        """
        Validate email format and check uniqueness.
        """
        email = value.lower().strip()
        if self.instance and self.instance.email == email:
            return email
        
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return email

    def update(self, instance, validated_data):
        """
        Update user with optional password change.
        """
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


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
            'cnic',
            'is_active',
            'date_joined',
            'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

