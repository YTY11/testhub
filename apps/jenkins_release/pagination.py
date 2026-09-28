from rest_framework.pagination import PageNumberPagination


class JenkinsBuildRecordPagination(PageNumberPagination):
    """构建记录分页类

    - 默认每页 20 条
    - 允许前端通过 ?page_size=xx 覆盖
    - 单页最大 100 条，防止前端传超大值拉爆内存
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'