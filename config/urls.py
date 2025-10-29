
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('users.urls')),
    path('api/v1/auth/', include('djoser.urls')),
    path('api/v1/cpd/', include('cpd_tracking.urls')),
    path('api/v1/programs/', include('cpd_managements.urls')),
    path('api/v1/activities/', include('cpd_activities.urls')),
    path('api/v1/chats/', include('chats.urls')),
    path('api/v1/subscriptions/', include('subscriptions.urls')),
]
