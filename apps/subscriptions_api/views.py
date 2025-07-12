from rest_framework import viewsets
from .models import UserSubscription, SubscriptionPlan
from .serializers import  SubscriptionPlanSerializer , UserSubscriptionSerializer
from .permissions import IsSuperuserOrReadOnly
from rest_framework.permissions import IsAuthenticated

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsSuperuserOrReadOnly , IsAuthenticated]

    filterset_fields = ['is_active']
    search_fields = ['name', ]
    ordering_fields = ['price', 'duration_days']


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return UserSubscription.objects.all()
        return UserSubscription.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)