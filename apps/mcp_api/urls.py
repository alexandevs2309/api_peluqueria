from django.urls import path

from .views import McpCallView, McpChatView, McpToolsView, TenantAiCredentialView

urlpatterns = [
    path("tools/", McpToolsView.as_view(), name="mcp-tools"),
    path("call/", McpCallView.as_view(), name="mcp-call"),
    path("chat/", McpChatView.as_view(), name="mcp-chat"),
    path("ai-credential/", TenantAiCredentialView.as_view(), name="mcp-ai-credential"),
]
