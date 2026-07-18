from django.urls import path
from apps.chatbot_api.views import ChatBotView

urlpatterns = [
    path('', ChatBotView.as_view(), name='chatbot_chat'),
]
