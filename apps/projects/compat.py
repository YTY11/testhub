"""四个测试模块共用的统一项目兼容接口。"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, serializers, viewsets
from rest_framework.exceptions import PermissionDenied

from .models import Project, ProjectAlias, ProjectMember
from .permissions import can_manage_project, get_user_role
from .unified import (
    ensure_project_unification,
    get_legacy_model,
    get_project_shadow,
    replace_project_members,
    sync_project_shadows,
    to_legacy_status,
    to_unified_status,
)

User = get_user_model()


class NullableDateField(serializers.DateField):
    """兼容前端传空字符串的日期字段。"""

    def to_internal_value(self, value):
        if value == '' or value is None:
            return None
        return super().to_internal_value(value)


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name'
        ]


class ModuleShadowField(serializers.Field):
    """
    读写模块影子项目的字段（base_url / project_type / default_env 等）。

    - 输出：读取模块历史项目（影子）上对应字段的值。
    - 输入：原样透传进 validated_data，由 update/create 写回影子项目，
      从而解决“前端更新 base_url 提示成功但没生效”的问题。
    """

    def __init__(self, attr, **kwargs):
        self.attr = attr
        kwargs.setdefault('required', False)
        kwargs.setdefault('allow_null', True)
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        # 让 to_representation 能拿到序列化器上下文里的 module
        context = parent.context if hasattr(parent, 'context') else {}
        self.module = context.get('module') if isinstance(context, dict) else None

    def get_attribute(self, instance):
        # 不直接读 instance 上的同名属性，交给 to_representation 从影子读取
        return instance

    def to_internal_value(self, data):
        return data

    def to_representation(self, instance):
        module = getattr(self, 'module', None)
        if not module:
            return ''
        shadow = get_project_shadow(instance, module)
        return getattr(shadow, self.attr, '')


class UnifiedProjectSerializer(serializers.ModelSerializer):
    """
    对外保持各模块原有项目字段。

    注意：
    - id 返回当前模块历史项目 ID，保证原有子资源接口继续可用。
    - source_id 返回统一 Project ID。
    """

    id = serializers.SerializerMethodField(read_only=True)
    source_id = serializers.IntegerField(read_only=True)

    owner = UserBriefSerializer(read_only=True)
    members = serializers.SerializerMethodField(read_only=True)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    can_manage = serializers.SerializerMethodField(read_only=True)
    owner_id = serializers.IntegerField(write_only=True, required=False)

    project_type = ModuleShadowField('project_type')
    base_url = ModuleShadowField('base_url')
    default_env = ModuleShadowField('default_env')

    start_date = NullableDateField(
        required=False,
        allow_null=True
    )
    end_date = NullableDateField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            'id',
            'source_id',
            'name',
            'description',
            'status',
            'owner',
            'members',
            'member_ids',
            'owner_id',
            'can_manage',
            'project_type',
            'base_url',
            'default_env',
            'start_date',
            'end_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'source_id',
            'owner',
            'created_at',
            'updated_at'
        ]

    def get_module(self):
        return self.context['module']

    def get_id(self, obj):
        shadow = get_project_shadow(obj, self.get_module())
        return shadow.pk if shadow else obj.pk

    def get_members(self, obj):
        members = [
            item.user
            for item in obj.projectmember_set.select_related('user')
        ]
        return UserBriefSerializer(members, many=True).data

    def get_can_manage(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return get_user_role(request.user, obj) in ('superuser', 'owner', 'admin')

    def _get_shadow(self, obj):
        return get_project_shadow(obj, self.get_module())

    def get_project_type(self, obj):
        shadow = self._get_shadow(obj)
        return getattr(shadow, 'project_type', 'HTTP')

    def get_base_url(self, obj):
        shadow = self._get_shadow(obj)
        return getattr(shadow, 'base_url', '')

    def get_default_env(self, obj):
        shadow = self._get_shadow(obj)
        return getattr(shadow, 'default_env', {})

    def get_start_date(self, obj):
        shadow = self._get_shadow(obj)
        return getattr(shadow, 'start_date', None)

    def get_end_date(self, obj):
        shadow = self._get_shadow(obj)
        return getattr(shadow, 'end_date', None)

    def to_internal_value(self, data):
        """兼容旧模块上传的 IN_PROGRESS 等大写状态。"""

        if hasattr(data, 'copy'):
            data = data.copy()

        status = data.get('status')
        if status in ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED'):
            data['status'] = to_unified_status(status)

        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # 模块旧前端通常使用 NOT_STARTED / IN_PROGRESS / COMPLETED。
        data['status'] = to_legacy_status(instance.status)
        data['id'] = self.get_id(instance)

        return data

    def _pop_module_extra_data(self, validated_data):
        fields = (
            'project_type',
            'base_url',
            'default_env',
            'start_date',
            'end_date'
        )
        return {
            field: validated_data.pop(field)
            for field in fields
            if field in validated_data
        }

    def _apply_module_extra_data(
        self,
        project,
        module,
        extra_data,
        created=False
    ):
        if not extra_data:
            return

        shadow = get_project_shadow(project, module)
        if shadow is None:
            return

        changed_fields = []

        if 'project_type' in extra_data and hasattr(
            shadow, 'project_type'
        ):
            shadow.project_type = extra_data['project_type']
            changed_fields.append('project_type')

        if 'base_url' in extra_data and hasattr(shadow, 'base_url'):
            value = extra_data['base_url'] or 'http://localhost'
            shadow.base_url = value
            changed_fields.append('base_url')

        if 'default_env' in extra_data and hasattr(
            shadow, 'default_env'
        ):
            shadow.default_env = extra_data['default_env'] or {}
            changed_fields.append('default_env')

        if 'start_date' in extra_data and hasattr(
            shadow, 'start_date'
        ):
            shadow.start_date = extra_data['start_date']
            changed_fields.append('start_date')

        if 'end_date' in extra_data and hasattr(
            shadow, 'end_date'
        ):
            shadow.end_date = extra_data['end_date']
            changed_fields.append('end_date')

        if changed_fields:
            shadow.save(update_fields=changed_fields)

    def create(self, validated_data):
        module = self.get_module()
        member_ids = validated_data.pop('member_ids', [])
        owner_id = validated_data.pop('owner_id', None)
        extra_data = self._pop_module_extra_data(validated_data)

        request = self.context['request']
        owner = request.user
        if owner_id and request.user.is_superuser:
            try:
                owner = User.objects.get(pk=owner_id)
            except User.DoesNotExist:
                owner = request.user

        with transaction.atomic():
            project = Project.objects.create(
                owner=owner,
                **validated_data
            )

            replace_project_members(project, member_ids)

            # 信号可能已经创建过兼容项目，这里再确保一次。
            sync_project_shadows(project)

            self._apply_module_extra_data(
                project,
                module,
                extra_data,
                created=True
            )

        return project

    def update(self, instance, validated_data):
        module = self.get_module()
        member_ids = validated_data.pop('member_ids', None)
        owner_id = validated_data.pop('owner_id', None)
        request = self.context.get('request')
        owner_changed = bool(owner_id and request and request.user.is_superuser)
        if owner_changed:
            instance.owner_id = owner_id
        extra_data = self._pop_module_extra_data(validated_data)

        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)

            save_fields = list(validated_data.keys())
            if owner_changed:
                save_fields.append('owner')
            instance.save(update_fields=save_fields or ['updated_at'])

            if member_ids is not None:
                replace_project_members(instance, member_ids)

            sync_project_shadows(instance)

            self._apply_module_extra_data(
                instance,
                module,
                extra_data,
                created=False
            )

        return instance


class UnifiedModuleProjectViewSet(viewsets.ModelViewSet):
    """各模块统一项目兼容 ViewSet。"""

    module = None
    serializer_class = UnifiedProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if not self.module:
            raise NotImplementedError(
                'UnifiedModuleProjectViewSet 必须设置 module'
            )

    def get_queryset(self):
        ensure_project_unification()

        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(
            Q(owner=user) |
            Q(projectmember__user=user)
        ).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['module'] = self.module
        return context

    def get_object(self):
        ensure_project_unification()

        pk = self.kwargs.get(
            self.lookup_url_kwarg or self.lookup_field
        )

        alias = ProjectAlias.objects.filter(
            module=self.module,
            legacy_project_id=pk
        ).select_related(
            'project'
        ).first()

        project_id = alias.project_id if alias else pk
        queryset = self.filter_queryset(self.get_queryset())

        obj = get_object_or_404(queryset, pk=project_id)
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_update(self, serializer):
        """更新项目需具备管理权限（超管 / 负责人 / admin）。"""
        if not can_manage_project(self.request.user, serializer.instance):
            raise PermissionDenied('无权限修改该项目')
        serializer.save()

    def perform_destroy(self, instance):
        """
        删除统一项目时，会同步删除四个模块的兼容项目行。
        仅超管 / 负责人 / admin 可删除，普通成员（developer/tester/viewer）禁止。
        """
        if not can_manage_project(self.request.user, instance):
            raise PermissionDenied('无权限删除该项目')
        instance.delete()


class ApiProjectCompatViewSet(UnifiedModuleProjectViewSet):
    module = 'api'


class UiProjectCompatViewSet(UnifiedModuleProjectViewSet):
    module = 'ui'


class AppProjectCompatViewSet(UnifiedModuleProjectViewSet):
    module = 'app'


class PerfProjectCompatViewSet(UnifiedModuleProjectViewSet):
    module = 'perf'
