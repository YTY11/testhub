from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserProfile

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'avatar')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'avatar', 'phone', 'department', 'position', 'is_active',
                 'is_superuser', 'is_staff', 'role',
                 'date_joined', 'created_at', 'updated_at']
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """超级管理员创建用户。"""
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password',
            'first_name', 'last_name', 'phone',
            'department', 'position',
            'is_superuser', 'is_active'
        ]

    def create(self, validated_data):
        is_superuser = validated_data.pop('is_superuser', False)
        user = User.objects.create_user(**validated_data)
        user.is_superuser = is_superuser
        user.is_staff = is_superuser
        user.role = 'admin' if is_superuser else 'user'
        user.save(update_fields=['is_superuser', 'is_staff', 'role'])
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """超级管理员更新用户资料 / 角色 / 启禁用。"""

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'department', 'position',
            'is_superuser', 'is_active'
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        # 保持 is_staff / role 与超管角色一致（用于 Django 后台访问与系统角色）
        sync_fields = []
        if instance.is_staff != instance.is_superuser:
            instance.is_staff = instance.is_superuser
            sync_fields.append('is_staff')
        expected_role = 'admin' if instance.is_superuser else 'user'
        if instance.role != expected_role:
            instance.role = expected_role
            sync_fields.append('role')
        if sync_fields:
            instance.save(update_fields=sync_fields)
        return instance

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm',
                 'first_name', 'last_name', 'phone', 'department', 'position']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密码不一致")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('用户已被禁用')
        else:
            raise serializers.ValidationError('用户名和密码不能为空')
        
        attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'