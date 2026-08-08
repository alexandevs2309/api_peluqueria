from rest_framework import viewsets, permissions
from .models import Tutorial
from .serializers import TutorialSerializer
from apps.core.permissions import IsSuperAdmin


class TutorialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tutorial.objects.filter(is_published=True)
    serializer_class = TutorialSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)
        return qs


class AdminTutorialViewSet(viewsets.ModelViewSet):
    queryset = Tutorial.objects.all()
    serializer_class = TutorialSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)
        return qs
