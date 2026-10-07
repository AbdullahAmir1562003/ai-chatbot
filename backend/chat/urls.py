from django.urls import path
from .views import (
    index,
    ConversationListCreateView,
    ConversationDetailView,
    SendMessageView,
)

urlpatterns = [
    path('', index, name='index'),
    path('api/conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
    path('api/conversations/<uuid:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('api/conversations/<uuid:conversation_id>/send/', SendMessageView.as_view(), name='send-message'),
]