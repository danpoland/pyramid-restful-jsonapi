import math

from pyramid.response import Response

from pyramid_restful.pagination import PageNumberPagination
from pyramid_restful.pagination.utilities import replace_query_param


class JSONAPIPagination(PageNumberPagination):
    """
    Page number pagination for JSON API formatted responses.
    """

    max_page_size = 50
    page_query_param = 'page[number]'
    page_size_query_param = 'page[size]'

    def get_paginated_response(self, data):
        links = data.get('links', {})
        first_url = self.get_first_link()
        last_url = self.get_last_link()
        next_url = self.get_next_link()
        previous_url = self.get_previous_link()

        links['next'] = next_url
        links['prev'] = previous_url
        links['first'] = first_url
        links['last'] = last_url
        data['links'] = links

        meta = data.get('meta', {})
        meta['count'] = self.page.paginator.count
        data['meta'] = meta

        return Response(json=data)

    def get_first_link(self):
        url = self.request.current_route_url()
        return replace_query_param(url, self.page_query_param, 1)

    def get_last_link(self):
        url = self.request.current_route_url()
        count = self.page.paginator.count
        page_size = self.get_page_size(self.request)
        total_pages = int(math.ceil(count / float(page_size)))
        return replace_query_param(url, self.page_query_param, total_pages)