from django.contrib import admin
from .models import ChatSession, Message

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'user__email', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-updated_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'sender', 'content_preview', 'created_at']
    list_filter = ['sender', 'created_at', 'session']
    search_fields = ['content', 'session__title', 'session__user__email']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
