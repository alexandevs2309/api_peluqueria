"""Paginación con techo explícito.

``LimitOffsetPagination`` de DRF no aplica ``MAX_PAGE_SIZE``: sin un ``max_limit``
un cliente puede pedir ``?limit=1000000`` y forzar la serialización de toda una
tabla. Este subclass conserva el default de 25 y solo acota el techo.
"""
from rest_framework.pagination import LimitOffsetPagination


class BoundedLimitOffsetPagination(LimitOffsetPagination):
    max_limit = 200
