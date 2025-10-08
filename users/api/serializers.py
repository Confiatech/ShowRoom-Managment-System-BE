from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user management"""
    password = serializers.CharField(write_only=True, required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    show_room_owner_email = serializers.CharField(source='show_room_owner.email', read_only=True)
    show_room_owner_name = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'role', 
            'show_room_owner', 'show_room_owner_email', 'show_room_owner_name','show_room_name',
            'cnic', 'phone_number', 'address', 'password', 'is_active', 'date_joined','image'
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
        import logging
        logger = logging.getLogger(__name__)
        
        password = validated_data.pop('password', None)
        
        # Debug: Print what we received
        logger.info(f"UserSerializer update - validated_data keys: {list(validated_data.keys())}")
        logger.info(f"Image field present: {'image' in validated_data}")
        
        print(f"UserSerializer update - validated_data keys: {list(validated_data.keys())}")
        print(f"Image field present: {'image' in validated_data}")
        
        if 'image' in validated_data:
            logger.info(f"Image value: {validated_data['image']}")
            logger.info(f"Image type: {type(validated_data['image'])}")
            print(f"Image value: {validated_data['image']}")
            print(f"Image type: {type(validated_data['image'])}")
        
        # Handle image field explicitly BEFORE other fields
        image = validated_data.pop('image', None)  # Use pop instead of get
        if image is not None:
            logger.info(f"Updating image from {instance.image} to {image}")
            print(f"Updating image from {instance.image} to {image}")
            # Delete old image if it exists
            if instance.image:
                old_image_path = instance.image.path
                instance.image.delete(save=False)
                logger.info(f"Deleted old image: {old_image_path}")
                print(f"Deleted old image: {old_image_path}")
            instance.image = image
            logger.info(f"Set new image: {instance.image}")
            print(f"Set new image: {instance.image}")
        else:
            logger.info("No image field found in validated_data")
            print("No image field found in validated_data")
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        logger.info(f"After save - image path: {instance.image}")
        print(f"After save - image path: {instance.image}")
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
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'phone_number', 'password', 'image', 'show_room_name'
        ]
    
    def validate_email(self, value):
        """Validate email format and check uniqueness"""
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return email
    
    def create(self, validated_data):
        # Set role to show_room_owner
        validated_data['role'] = 'show_room_owner'
        
        password = validated_data.pop('password', None)
        email = validated_data.pop('email')
        
        # Debug: Print what we received
        print(f"Creating show room owner with data: {validated_data}")
        print(f"Image field present: {'image' in validated_data}")
        if 'image' in validated_data:
            print(f"Image value: {validated_data['image']}")
        
        # Create user using the manager's create_user method to handle email properly
        user = User.objects.create_user(
            email=email,
            password=password or 'defaultpassword123',
            **validated_data
        )
        
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        email = validated_data.pop('email', None)
        
        # Handle image field explicitly
        image = validated_data.get('image')
        if image is not None:
            # Delete old image if it exists
            if instance.image:
                instance.image.delete(save=False)
            instance.image = image
        
        # Update email if provided
        if email:
            instance.email = email
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance