"""项目级权限辅助。

统一项目下的访问与成员管理判断：
- 可查看：超级管理员 / 项目负责人 / 项目成员。
- 可管理（改项目信息、增删改成员、删除项目）：超级管理员 / 负责人 / 管理员(admin)。
"""

from django.db.models import Q

from .models import ProjectMember

MANAGE_ROLES = {'owner', 'admin'}


def project_access_q(user):
    """
    各模块历史项目视图（UiProject / ApiProject / AppProject 等）的访问过滤条件。

    统一权限下：
    - 超级管理员可见全部模块项目；
    - 其余用户可见其负责（owner）或作为成员（members）的项目。
    返回一个 Q 对象，可直接用于 .filter(...)。
    """
    if user.is_superuser:
        return Q()
    return Q(owner=user) | Q(members=user)


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
