from django.urls import path
from .views import ChatSessionListView, MessageView, ChatSessionDetailView

urlpatterns = [
    path('messages/', MessageView.as_view(), name='message-create'),
    path('<str:session_id>/messages/', MessageView.as_view(), name='message-create-session'),

    path('', ChatSessionListView.as_view(), name='chat-session-list'),
    path('<str:id>/', ChatSessionDetailView.as_view(), name='chat-session-detail'),
]