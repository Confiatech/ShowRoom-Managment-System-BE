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
            'role',
            'show_room_owner'
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
    image = serializers.ImageField(required=False, allow_null=True)

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
            'show_room_owner',
            'is_active',
            'image',
            'show_room_name'
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
        Update user with optional password change and image handling.
        """
        password = validated_data.pop('password', None)
        
        # Handle image field explicitly
        image = validated_data.pop('image', None)
        if image is not None:
            # Delete old image if it exists
            if instance.image:
                instance.image.delete(save=False)
            instance.image = image
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for password reset by show room owner.
    Only requires new password, no old password needed.
    """
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="New password for the user (minimum 8 characters)"
    )

    def validate_new_password(self, value):
        """
        Validate the new password.
        """
        try:
            validate_password(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return value


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data in responses.
    """
    show_room_owner_email = serializers.CharField(source='show_room_owner.email', read_only=True)
    
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
            'show_room_owner',
            'show_room_owner_email',
            'is_active',
            'date_joined',
            'last_login',
            'image',
            'show_room_name',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'show_room_owner_email']

