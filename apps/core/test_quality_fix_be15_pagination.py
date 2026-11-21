"""BE-15: REST_FRAMEWORK['MAX_PAGE_SIZE'] es la única fuente del techo."""
from django.conf import settings
from django.test import RequestFactory
from rest_framework.request import Request

from apps.core.pagination import BoundedLimitOffsetPagination


def test_quality_fix_be15_settings_and_paginator_are_aligned():
    paginator = BoundedLimitOffsetPagination()
    assert settings.REST_FRAMEWORK['MAX_PAGE_SIZE'] == paginator.max_limit == 200


def test_quality_fix_be15_limit_150_is_honoured():
    paginator = BoundedLimitOffsetPagination()
    request = Request(RequestFactory().get('/?limit=150'))
    page = paginator.paginate_queryset(list(range(200)), request)

    assert paginator.limit == 150
    assert len(page) == 150


def test_quality_fix_be15_limit_above_max_is_capped():
    paginator = BoundedLimitOffsetPagination()
    request = Request(RequestFactory().get('/?limit=500'))

    page = paginator.paginate_queryset(list(range(500)), request)

    assert paginator.limit == 200
    assert len(page) == 200
