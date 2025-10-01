from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, LogoutView,
    ChangePasswordView, PasswordResetRequestView, PasswordResetConfirmView,ActiveSessionsView , TerminateSessionView , VerifyEmailView , MFALoginVerifyView , MFASetupView , MFAVerifyView, UserViewSet
)
from .permissions_check import UserPermissionsView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view() , name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('reset-password/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('reset-password-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('active-sessions/', ActiveSessionsView.as_view(), name='active-sessions'),
    path('session/<str:jti>/', TerminateSessionView.as_view(), name='terminate-session'),
    path('verify-email/<str:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('mfa/setup/', MFASetupView.as_view(), name='mfa-setup'),
    path('mfa/verify/', MFAVerifyView.as_view(), name='mfa-verify'),
    path('mfa/login-verify/', MFALoginVerifyView.as_view(), name='mfa-login-verify'),
    path('permissions/', UserPermissionsView.as_view(), name='user-permissions'),
    path('', include(router.urls)),
]
