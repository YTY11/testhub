from rest_framework import serializers
from .models import Project, ProjectMember, ProjectEnvironment
from .permissions import get_user_role
from apps.users.serializers import UserSerializer

class ProjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'name')

class ProjectEnvironmentSerializer(serializers.ModelSerializer):
    base_url = serializers.CharField(required=True, allow_blank=False)
    class Meta:
        model = ProjectEnvironment
        fields = '__all__'
        extra_kwargs = {
            'project': {'read_only': True},
        }

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']

    def validate_role(self, value):
        choices = dict(ProjectMember.ROLE_CHOICES)
        if value not in choices:
            raise serializers.ValidationError('无效的项目角色')
        return value

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = ProjectMemberSerializer(source='projectmember_set', many=True, read_only=True)
    environments = ProjectEnvironmentSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(source='projectmember_set.count', read_only=True)
    current_user_role = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField(write_only=True, required=False)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'owner', 'members',
                  'environments', 'member_count', 'current_user_role', 'can_manage',
                  'owner_id', 'member_ids',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_current_user_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return get_user_role(request.user, obj)

    def get_can_manage(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return get_user_role(request.user, obj) in ('superuser', 'owner', 'admin')

    def update(self, instance, validated_data):
        request = self.context.get('request')
        owner_id = validated_data.pop('owner_id', None)
        member_ids = validated_data.pop('member_ids', None)

        # 仅超级管理员可改负责人
        if owner_id and request and request.user.is_superuser:
            instance.owner_id = owner_id

        instance = super().update(instance, validated_data)

        # member_ids 未传时保持成员不变；传入则按列表对账（加新成员、移除取消的成员）
        if member_ids is not None:
            self._sync_members(instance, member_ids)

        return instance

    def _sync_members(self, instance, member_ids):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        member_ids = {int(i) for i in member_ids}
        # 负责人不算普通成员，不参与增删
        member_ids.discard(instance.owner_id)

        current = set(
            ProjectMember.objects.filter(project=instance)
            .values_list('user_id', flat=True)
        )

        # 移除已取消的成员（保留负责人的成员行）
        ProjectMember.objects.filter(project=instance) \
            .exclude(user_id=instance.owner_id) \
            .exclude(user_id__in=member_ids) \
            .delete()

        # 新增成员
        to_add = member_ids - current
        if to_add:
            members = User.objects.filter(id__in=to_add, is_active=True)
            ProjectMember.objects.bulk_create(
                [
                    ProjectMember(project=instance, user=u, role='tester')
                    for u in members
                ],
                ignore_conflicts=True
            )

class ProjectCreateSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(write_only=True, required=False)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'owner_id', 'member_ids']
    
    def create(self, validated_data):
        request = self.context['request']
        member_ids = validated_data.pop('member_ids', [])
        owner_id = validated_data.pop('owner_id', None)

        # 仅超级管理员可指定负责人，其余默认创建者为负责人。
        if owner_id and request.user.is_superuser:
            validated_data['owner_id'] = owner_id
        else:
            validated_data['owner'] = request.user

        project = super().create(validated_data)

        member_ids = [m for m in member_ids if m != project.owner_id]
        if member_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            members = User.objects.filter(id__in=member_ids, is_active=True)
            ProjectMember.objects.bulk_create(
                [
                    ProjectMember(project=project, user=u, role='tester')
                    for u in members
                ],
                ignore_conflicts=True
            )

        return project
