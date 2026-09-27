"""统一项目管理与历史项目表同步服务。"""

from django.apps import apps
from django.db import connection, transaction

from .models import Project, ProjectAlias, ProjectMember


MODULE_MODELS = {
    'api': ('api_testing', 'ApiProject'),
    'ui': ('ui_automation', 'UiProject'),
    'app': ('app_automation', 'AppProject'),
    'perf': ('perf_testing', 'PerfProject'),
}

LEGACY_TO_UNIFIED_STATUS = {
    'NOT_STARTED': 'paused',
    'IN_PROGRESS': 'active',
    'COMPLETED': 'completed',
}

UNIFIED_TO_LEGACY_STATUS = {
    'active': 'IN_PROGRESS',
    'paused': 'NOT_STARTED',
    'completed': 'COMPLETED',
    'archived': 'COMPLETED',
}


def _table_exists(model):
    return model._meta.db_table in connection.introspection.table_names()


def get_legacy_model(module):
    app_label, model_name = MODULE_MODELS[module]
    return apps.get_model(app_label, model_name)


def to_unified_status(status):
    return LEGACY_TO_UNIFIED_STATUS.get(status, status or 'active')


def to_legacy_status(status):
    return UNIFIED_TO_LEGACY_STATUS.get(status, 'IN_PROGRESS')


def get_project_shadow(project, module):
    """获取统一项目在某个模块中的历史项目行。"""

    if not _table_exists(ProjectAlias):
        return None

    alias = ProjectAlias.objects.filter(
        project=project,
        module=module
    ).first()

    if not alias:
        return None

    model = get_legacy_model(module)
    return model.objects.filter(pk=alias.legacy_project_id).first()


def replace_project_members(project, member_ids):
    """替换统一项目成员，并同步到所有模块历史项目表。"""

    member_ids = list(dict.fromkeys(member_ids or []))

    project.projectmember_set.all().delete()

    if member_ids:
        ProjectMember.objects.bulk_create(
            [
                ProjectMember(
                    project=project,
                    user_id=user_id,
                    role='tester'
                )
                for user_id in member_ids
            ],
            ignore_conflicts=True
        )

    sync_project_shadows(project)


def sync_project_shadows(project):
    """
    同步统一项目的公共字段到四个模块的历史项目表。

    只同步：
    - name
    - description
    - status
    - members

    不同步模块特有配置，避免互相覆盖。
    """

    if not _table_exists(ProjectAlias):
        return

    # 项目已被删除（或其删除已提交）时，不再重建影子/别名，
    # 否则会往 project_aliases 插入指向已删除 project_id 的行，触发外键 1452。
    if not Project.objects.filter(pk=project.pk).exists():
        return

    members = list(project.members.all())

    for module in MODULE_MODELS:
        model = get_legacy_model(module)

        if not _table_exists(model):
            continue

        alias = ProjectAlias.objects.filter(
            project=project,
            module=module
        ).first()

        shadow = None

        if alias:
            shadow = model.objects.filter(
                pk=alias.legacy_project_id
            ).first()

            if shadow is None:
                alias.delete()
                alias = None

        if shadow is None:
            # 优先复用同名称、同负责人的历史项目，避免重复创建。
            shadow = model.objects.filter(
                name=project.name,
                owner=project.owner
            ).order_by('id').first()

        if shadow is None:
            fields = {
                'name': project.name,
                'description': project.description or '',
                'status': to_legacy_status(project.status),
                'owner': project.owner,
            }

            if module == 'api':
                fields['project_type'] = 'HTTP'
            elif module == 'ui':
                fields['base_url'] = 'http://localhost'
            elif module == 'perf':
                fields['default_env'] = {}

            shadow = model.objects.create(**fields)

        ProjectAlias.objects.get_or_create(
            project=project,
            module=module,
            defaults={
                'legacy_project_id': shadow.pk
            }
        )

        changed_fields = []

        common_values = {
            'name': project.name,
            'description': project.description or '',
            'status': to_legacy_status(project.status),
        }

        for field_name, value in common_values.items():
            if getattr(shadow, field_name) != value:
                setattr(shadow, field_name, value)
                changed_fields.append(field_name)

        if changed_fields:
            shadow.save(update_fields=changed_fields)

        if hasattr(shadow, 'members'):
            shadow.members.set(members)


def delete_project_shadows(project):
    """删除统一项目对应的四个模块历史项目行。"""

    if not _table_exists(ProjectAlias):
        return

    aliases = list(
        ProjectAlias.objects.filter(project=project).select_related('project')
    )

    for alias in aliases:
        model = get_legacy_model(alias.module)

        if _table_exists(model):
            model.objects.filter(
                pk=alias.legacy_project_id
            ).delete()

        alias.delete()


def ensure_project_unification():
    """
    幂等初始化：

    1. 将各模块已有项目按“项目名称 + 负责人”归并到统一 Project。
    2. 建立 ProjectAlias。
    3. 为统一项目补齐四个模块的兼容项目行。
    """

    if not _table_exists(ProjectAlias):
        return

    for module in MODULE_MODELS:
        model = get_legacy_model(module)

        if not _table_exists(model):
            continue

        legacy_projects = model.objects.select_related(
            'owner'
        ).prefetch_related(
            'members'
        ).order_by('id')

        for legacy_project in legacy_projects:
            alias = ProjectAlias.objects.filter(
                module=module,
                legacy_project_id=legacy_project.pk
            ).first()

            if alias and Project.objects.filter(
                pk=alias.project_id
            ).exists():
                continue

            if alias:
                alias.delete()

            unified_project = Project.objects.filter(
                name=legacy_project.name,
                owner=legacy_project.owner
            ).order_by('id').first()

            if unified_project is None:
                with transaction.atomic():
                    unified_project = Project.objects.create(
                        name=legacy_project.name,
                        description=legacy_project.description or '',
                        status=to_unified_status(legacy_project.status),
                        owner=legacy_project.owner
                    )

                    for member in legacy_project.members.all():
                        ProjectMember.objects.get_or_create(
                            project=unified_project,
                            user=member,
                            defaults={
                                'role': 'tester'
                            }
                        )

            ProjectAlias.objects.get_or_create(
                project=unified_project,
                module=module,
                defaults={
                    'legacy_project_id': legacy_project.pk
                }
            )

    for project in Project.objects.select_related(
        'owner'
    ).prefetch_related(
        'members'
    ).order_by('id'):
        sync_project_shadows(project)