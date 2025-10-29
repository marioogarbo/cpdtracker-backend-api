from uuid import uuid4
from django.db import models
from django.conf import settings
from config.utils import CustomShortUUIDField

User = settings.AUTH_USER_MODEL

class ChatSession(models.Model):
    id =  CustomShortUUIDField(primary_key=True, prefix='session_', editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats')
    title = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'Chat {self.id} - {self.title or "Untitled"}'

class Message(models.Model):
    id =   CustomShortUUIDField(primary_key=True, prefix='msg_', editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('ai', 'AI')])    
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f'Message {self.id} in {self.session.title or "Untitled"}'