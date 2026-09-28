from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import JenkinsBuildRecord
from .serializers import JenkinsBuildRecordSerializer, JenkinsBuildReportSerializer
from .pagination import JenkinsBuildRecordPagination        # ← 新增 import


class JenkinsBuildRecordViewSet(viewsets.ModelViewSet):
    """构建记录 CRUD（列表/详情/编辑/删除需登录）"""
    queryset = JenkinsBuildRecord.objects.all()
    serializer_class = JenkinsBuildRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = JenkinsBuildRecordPagination          # ← 新增这一行

    # ---------- 查询过滤 ----------
    def get_queryset(self):
        qs = super().get_queryset()
        project_name = self.request.query_params.get('project_name')
        result = self.request.query_params.get('build_result')
        job_name = self.request.query_params.get('job_name')
        branch = self.request.query_params.get('branch')
        deploy_env = self.request.query_params.get('deploy_env')
        trigger_type = self.request.query_params.get('trigger_type')
        parent_build_number = self.request.query_params.get('parent_build_number')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if project_name:
            qs = qs.filter(project_name__icontains=project_name)
        if result:
            qs = qs.filter(build_result=result)
        if job_name:
            qs = qs.filter(job_name__icontains=job_name)
        if branch:
            qs = qs.filter(branch__icontains=branch)
        if deploy_env:
            qs = qs.filter(deploy_env=deploy_env)
        if trigger_type:
            qs = qs.filter(trigger_type=trigger_type)
        if parent_build_number:
            qs = qs.filter(parent_build_number=parent_build_number)
        if start_date:
            qs = qs.filter(start_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(start_time__date__lte=end_date)
        return qs

    # ---------- 空字符串清洗 ----------
    def _clean_empty(self, data):
        """把可空字段的空字符串统一转 None，避免 DateTimeField 校验报错"""
        nullable = ('start_time', 'end_time', 'parent_build_number')
        out = data.copy() if hasattr(data, 'copy') else dict(data)
        for k in nullable:
            if out.get(k) == '':
                out[k] = None
        return out

    def create(self, request, *args, **kwargs):
        data = self._clean_empty(request.data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = self._clean_empty(request.data)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    # ---------- 批量删除 ----------
    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除构建记录

        请求体：
            {"ids": [1, 2, 3]}
        返回：
            {"deleted": 3, "not_found": []}
        """
        ids = request.data.get('ids', [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {'detail': 'ids 必须是非空数组'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return Response(
                {'detail': 'ids 中包含非法值'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = JenkinsBuildRecord.objects.filter(id__in=ids)
        existing_ids = list(qs.values_list('id', flat=True))
        not_found = list(set(ids) - set(existing_ids))

        qs.delete()

        return Response({
            'deleted': len(existing_ids),
            'not_found': not_found,
        }, status=status.HTTP_200_OK)

    # ---------- Jenkins 上报（公开接口） ----------
    @action(
        detail=False,
        methods=['post'],
        url_path='report',
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def report(self, request):
        """Jenkins 回调上报接口（幂等，公开访问）"""
        secret = getattr(settings, 'JENKINS_REPORT_SECRET', '')
        if secret:
            if request.headers.get('X-Jenkins-Secret', '') != secret:
                return Response(
                    {'detail': 'Invalid secret'},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = JenkinsBuildReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        record, created = JenkinsBuildRecord.objects.update_or_create(
            job_name=data['job_name'],
            build_number=data['build_number'],
            defaults={
                'project_name': data['project_name'],
                'project_display_name': data.get('project_display_name', ''),
                'build_url': data.get('build_url', ''),
                'build_result': data['build_result'],
                'branch': data.get('branch', ''),
                'release_branch': data.get('release_branch', ''),
                'deploy_env': data.get('deploy_env', ''),
                'start_time': data.get('start_time'),
                'end_time': data.get('end_time'),
                'duration_ms': data.get('duration_ms', 0),
                'commit_sha': data.get('commit_sha', ''),
                'change_content': data.get('change_content', ''),
                'change_files': data.get('change_files', ''),
                'triggered_by': data.get('triggered_by', ''),
                'trigger_type': data.get('trigger_type', ''),
                'parent_job_name': data.get('parent_job_name', ''),
                'parent_build_number': data.get('parent_build_number'),
                # 注意：不包含 remark，避免 Jenkins 上报覆盖前端人工备注
            }
        )
        out = JenkinsBuildRecordSerializer(record)
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(out.data, status=http_status)