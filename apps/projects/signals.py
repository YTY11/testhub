from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import Project, ProjectMember
from .unified import (
    delete_project_shadows,
    sync_project_shadows,
)


def _schedule_sync(project):
    if not isinstance(project, Project):
        return

    transaction.on_commit(
        lambda: sync_project_shadows(project)
    )


@receiver(post_save, sender=Project)
def project_saved(sender, instance, created, **kwargs):
    _schedule_sync(instance)


@receiver(pre_delete, sender=Project)
def project_deleted(sender, instance, **kwargs):
    delete_project_shadows(instance)


@receiver(post_save, sender=ProjectMember)
def project_member_saved(sender, instance, created, **kwargs):
    _schedule_sync(instance.project)


@receiver(post_delete, sender=ProjectMember)
def project_member_deleted(sender, instance, **kwargs):
    _schedule_sync(instance.project)