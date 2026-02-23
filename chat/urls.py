from django.urls import path
from .views import ConversationListCreateAPIView, ConversationMessagesAPIView, ConversationMarkReadAPIView

urlpatterns = [
    path("conversations/", ConversationListCreateAPIView.as_view()),
    path("conversations/<uuid:public_id>/messages/", ConversationMessagesAPIView.as_view()),
    path("conversations/<uuid:public_id>/read/", ConversationMarkReadAPIView.as_view()),
]