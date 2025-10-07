from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user management"""
    password = serializers.CharField(write_only=True, required=False)
    show_room_owner_email = serializers.CharField(source='show_room_owner.email', read_only=True)
    show_room_owner_name = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'role', 
            'show_room_owner', 'show_room_owner_email', 'show_room_owner_name',
            'cnic', 'phone_number', 'address', 'password', 'is_active', 'date_joined'
        ]
        read_only_fields = ['date_joined']
    
    def get_show_room_owner_name(self, obj):
        """Get show room owner's full name"""
        if obj.show_room_owner:
            return f"{obj.show_room_owner.first_name or ''} {obj.show_room_owner.last_name or ''}".strip() or obj.show_room_owner.email
        return None
    
    def get_full_name(self, obj):
        """Get user's full name"""
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.email
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            user.set_password('defaultpassword123')  # Default password
        
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class InvestorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating investors by show room owners"""
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'cnic', 
            'phone_number', 'address', 'password'
        ]
    
    def create(self, validated_data):
        # Set role to investor and assign show room owner
        validated_data['role'] = 'investor'
        
        # Get show room owner from context
        request = self.context.get('request')
        if request and request.user.role == 'show_room_owner':
            validated_data['show_room_owner'] = request.user
        
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            user.set_password('defaultpassword123')  # Default password
        
        user.save()
        return user


class ShowRoomOwnerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating show room owners by super admin"""
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'cnic', 
            'phone_number', 'address', 'password'
        ]
    
    def create(self, validated_data):
        # Set role to show_room_owner
        validated_data['role'] = 'show_room_owner'
        
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            user.set_password('defaultpassword123')  # Default password
        
        user.save()
        return user