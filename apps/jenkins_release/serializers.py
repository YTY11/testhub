from rest_framework import serializers
from .models import JenkinsBuildRecord


class JenkinsBuildRecordSerializer(serializers.ModelSerializer):
    """供前端 CRUD 使用"""
    build_result_display = serializers.CharField(
        source='get_build_result_display', read_only=True
    )
    trigger_type_display = serializers.CharField(
        source='get_trigger_type_display', read_only=True
    )

    class Meta:
        model = JenkinsBuildRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class JenkinsBuildReportSerializer(serializers.Serializer):
    """Jenkins 回调上报"""
    project_name = serializers.CharField(max_length=100)
    project_display_name = serializers.CharField(
        required=False, default='', allow_blank=True
    )
    job_name = serializers.CharField(max_length=255)
    build_number = serializers.IntegerField()
    build_url = serializers.URLField(required=False, default='')
    build_result = serializers.ChoiceField(
        choices=['SUCCESS', 'FAILURE', 'ABORTED', 'UNSTABLE', 'BUILDING']
    )
    branch = serializers.CharField(required=False, default='', allow_blank=True)
    release_branch = serializers.CharField(required=False, default='', allow_blank=True)
    deploy_env = serializers.CharField(required=False, default='', allow_blank=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    duration_ms = serializers.IntegerField(required=False, default=0)
    commit_sha = serializers.CharField(required=False, default='', allow_blank=True)
    change_content = serializers.CharField(required=False, default='', allow_blank=True)
    change_files = serializers.CharField(required=False, default='', allow_blank=True)
    triggered_by = serializers.CharField(required=False, default='', allow_blank=True)
    trigger_type = serializers.CharField(required=False, default='', allow_blank=True)
    parent_job_name = serializers.CharField(required=False, default='', allow_blank=True)
    parent_build_number = serializers.IntegerField(required=False, allow_null=True)