"""项目级权限辅助。

统一项目下的访问与成员管理判断：
- 可查看：超级管理员 / 项目负责人 / 项目成员。
- 可管理（改项目信息、增删改成员、删除项目）：超级管理员 / 负责人 / 管理员(admin)。
"""

from .models import ProjectMember

MANAGE_ROLES = {'owner', 'admin'}


def get_user_role(user, project):
    """返回当前用户在项目中的角色，非成员返回 None。"""
    if user.is_superuser:
        return 'superuser'
    if user.id == project.owner_id:
        return 'owner'
    member = ProjectMember.objects.filter(
        project=project,
        user=user
    ).only('role').first()
    return member.role if member else None


def can_view_project(user, project):
    if user.is_superuser:
        return True
    if user.id == project.owner_id:
        return True
    return ProjectMember.objects.filter(
        project=project,
        user=user
    ).exists()


def can_manage_project(user, project):
    """能否管理项目信息与成员（增删改）。"""
    if user.is_superuser:
        return True
    if user.id == project.owner_id:
        return True
    return ProjectMember.objects.filter(
        project=project,
        user=user,
        role__in=MANAGE_ROLES
    ).exists()
