from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class UserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Returns the current user's permissions and superuser status
        """
        user = request.user
        return Response({
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'email': user.email,
            'full_name': user.full_name
        })
