from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.shortcuts import get_object_or_404
from .models import Project, ProjectMember, ProjectEnvironment
from .serializers import ProjectSerializer, ProjectCreateSerializer, ProjectMemberSerializer, ProjectEnvironmentSerializer
from .permissions import can_view_project, can_manage_project
from .unified import ensure_project_unification, sync_project_shadows


class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_queryset(self):
        ensure_project_unification()

        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()

    def perform_create(self, serializer):
        project = serializer.save()
        # 立即同步到各测试模块，保证统一创建后各模块立即可见。
        sync_project_shadows(project)



@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_projects(request):
    """获取统一项目，用于下拉选择等场景。

    超级管理员可看到全部项目；普通用户仅能看到自己负责或参与的项目。
    """
    ensure_project_unification()

    queryset = Project.objects.all()
    if not request.user.is_superuser:
        queryset = queryset.filter(
            models.Q(owner=request.user) |
            models.Q(members=request.user)
        ).distinct()

    projects = queryset.values(
        'id',
        'name',
        'description',
        'status'
    )
    return Response(list(projects))

class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()

    def perform_update(self, serializer):
        if not can_manage_project(self.request.user, serializer.instance):
            raise PermissionDenied('无权限修改该项目')
        serializer.save()
        sync_project_shadows(serializer.instance)

    def perform_destroy(self, instance):
        if not can_manage_project(self.request.user, instance):
            raise PermissionDenied('无权限删除该项目')
        instance.delete()

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_project_member(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
        if not can_manage_project(request.user, project):
            return Response({'error': '无权限添加成员'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProjectMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save(project=project)
        sync_project_shadows(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_members(request, project_id):
    """获取项目成员列表"""
    try:
        project = Project.objects.get(id=project_id)
        
        # 检查用户是否有权限查看项目成员
        if not can_view_project(request.user, project):
            return Response({'error': '无权限查看项目成员'}, status=status.HTTP_403_FORBIDDEN)
        
        # 获取项目成员，包括项目所有者
        members = []
        
        # 添加项目所有者
        members.append({
            'id': project.owner.id,
            'username': project.owner.username,
            'email': project.owner.email,
            'first_name': project.owner.first_name,
            'last_name': project.owner.last_name,
            'role': 'owner'
        })
        
        # 添加项目成员
        project_members = ProjectMember.objects.filter(project=project).select_related('user')
        for member in project_members:
            members.append({
                'id': member.user.id,
                'username': member.user.username,
                'email': member.user.email,
                'first_name': member.user.first_name,
                'last_name': member.user.last_name,
                'role': member.role,
                'member_id': member.id
            })
        
        return Response(members)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_project_member(request, project_id, member_id):
    try:
        project = Project.objects.get(id=project_id)
        if not can_manage_project(request.user, project):
            return Response({'error': '无权限删除成员'}, status=status.HTTP_403_FORBIDDEN)
        
        member = ProjectMember.objects.get(id=member_id, project=project)
        member.delete()
        sync_project_shadows(project)
        return Response({'message': '成员删除成功'})
    except (Project.DoesNotExist, ProjectMember.DoesNotExist):
        return Response({'error': '项目或成员不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_project_member_role(request, project_id, member_id):
    """修改项目成员角色。"""
    try:
        project = Project.objects.get(id=project_id)
        if not can_manage_project(request.user, project):
            return Response({'error': '无权限修改成员角色'}, status=status.HTTP_403_FORBIDDEN)

        role = request.data.get('role')
        valid_roles = dict(ProjectMember.ROLE_CHOICES)
        if role not in valid_roles:
            return Response({'error': '无效的项目角色'}, status=status.HTTP_400_BAD_REQUEST)

        member = ProjectMember.objects.get(id=member_id, project=project)
        member.role = role
        member.save(update_fields=['role'])
        return Response({
            'id': member.id,
            'user': member.user.id,
            'role': member.role
        })
    except (Project.DoesNotExist, ProjectMember.DoesNotExist):
        return Response({'error': '项目或成员不存在'}, status=status.HTTP_404_NOT_FOUND)

class ProjectEnvironmentListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_project(self):
        project = get_object_or_404(
            Project, pk=self.kwargs['project_id']
        )
        if not can_view_project(self.request.user, project):
            raise PermissionDenied('无权限访问该项目')
        return project

    def get_queryset(self):
        project = self._get_project()
        return ProjectEnvironment.objects.filter(project_id=project.pk)

    def perform_create(self, serializer):
        project = self._get_project()
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied('无权限管理该项目环境')
        serializer.save(project_id=project.pk)


class ProjectEnvironmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_project(self):
        project = get_object_or_404(
            Project, pk=self.kwargs['project_id']
        )
        if not can_view_project(self.request.user, project):
            raise PermissionDenied('无权限访问该项目')
        return project

    def get_queryset(self):
        project = self._get_project()
        return ProjectEnvironment.objects.filter(
            project_id=project.pk,
            pk=self.kwargs['pk']
        )

    def perform_update(self, serializer):
        project = self._get_project()
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied('无权限管理该项目环境')
        serializer.save()

    def perform_destroy(self, instance):
        project = self._get_project()
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied('无权限管理该项目环境')
        instance.delete()
