from django.db import models


class JenkinsBuildRecord(models.Model):
    BUILD_RESULT_CHOICES = [
        ('SUCCESS', '成功'),
        ('FAILURE', '失败'),
        ('ABORTED', '中止'),
        ('UNSTABLE', '不稳定'),
        ('BUILDING', '构建中'),
    ]

    TRIGGER_TYPE_CHOICES = [
        ('auto', '自动发版'),
        ('manual', '手动发布'),
    ]

    # ---- 项目信息 ----
    project_name = models.CharField(max_length=100, verbose_name='项目名称')
    project_display_name = models.CharField(
        max_length=100, blank=True, default='', verbose_name='项目显示名'
    )

    # ---- 构建标识 ----
    job_name = models.CharField(max_length=255, verbose_name='Jenkins Job 名称')
    build_number = models.PositiveIntegerField(verbose_name='构建编号')
    build_url = models.URLField(max_length=500, blank=True, default='', verbose_name='构建链接')

    # ---- 分支与环境 ----
    branch = models.CharField(max_length=255, blank=True, default='', verbose_name='源码分支')
    release_branch = models.CharField(
        max_length=255, blank=True, default='', verbose_name='发布分支'
    )
    deploy_env = models.CharField(max_length=20, blank=True, default='', verbose_name='部署环境')

    # ---- 构建结果 ----
    build_result = models.CharField(
        max_length=20, choices=BUILD_RESULT_CHOICES,
        default='BUILDING', verbose_name='构建结果'
    )

    # ---- 时间与耗时 ----
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration_ms = models.BigIntegerField(default=0, verbose_name='持续时间(毫秒)')

    # ---- 代码变更 ----
    commit_sha = models.CharField(max_length=64, blank=True, default='', verbose_name='Commit SHA')
    change_content = models.TextField(blank=True, default='', verbose_name='变更内容')
    change_files = models.TextField(blank=True, default='', verbose_name='变更文件')

    # ---- 触发信息 ----
    triggered_by = models.CharField(max_length=100, blank=True, default='', verbose_name='触发人')
    trigger_type = models.CharField(
        max_length=20, choices=TRIGGER_TYPE_CHOICES,
        blank=True, default='', verbose_name='触发类型'
    )
    parent_job_name = models.CharField(
        max_length=255, blank=True, default='', verbose_name='主流水线名称'
    )
    parent_build_number = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='主流水线构建号'
    )

    # ---- 备注（前端可编辑） ----
    remark = models.TextField(blank=True, default='', verbose_name='备注')

    # ---- 通用字段 ----
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'jenkins_build_record'
        verbose_name = 'Jenkins 构建记录'
        verbose_name_plural = verbose_name
        unique_together = [['job_name', 'build_number']]
        ordering = ['-start_time', '-created_at']
        indexes = [
            models.Index(fields=['project_name', '-start_time']),
            models.Index(fields=['build_result']),
            models.Index(fields=['branch']),
            models.Index(fields=['trigger_type']),
            models.Index(fields=['parent_job_name', 'parent_build_number']),
        ]

    def __str__(self):
        return f'{self.project_name} - {self.job_name} #{self.build_number} - {self.build_result}'