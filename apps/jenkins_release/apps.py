from django.apps import AppConfig


class JenkinsReleaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.jenkins_release'
    verbose_name = 'Jenkins 发布管理'