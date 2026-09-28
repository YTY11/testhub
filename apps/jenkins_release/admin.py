from django.contrib import admin
from .models import JenkinsBuildRecord


@admin.register(JenkinsBuildRecord)
class JenkinsBuildRecordAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project_name', 'job_name', 'build_number',
        'branch', 'release_branch', 'deploy_env', 'trigger_type',
        'build_result', 'duration_ms', 'start_time'
    ]
    search_fields = ['project_name', 'job_name', 'commit_sha', 'change_content']
    list_filter = ['build_result', 'deploy_env', 'trigger_type', 'branch']
    date_hierarchy = 'start_time'
    readonly_fields = ['created_at', 'updated_at']