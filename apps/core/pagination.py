"""全局标准分页器：在默认每页 20 条的基础上，支持通过 ?page_size= 指定单页条数（带上限）。"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500
