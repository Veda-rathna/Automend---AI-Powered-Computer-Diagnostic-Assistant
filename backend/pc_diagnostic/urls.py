"""
URL configuration for pc_diagnostic project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views
from . import mcp_views
from ai_diagnostic import conversation_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/diagnose/', views.diagnose, name='diagnose'),
    path('api/predict/', views.predict, name='predict'),
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/telemetry/', views.get_telemetry, name='get_telemetry'),
    path('api/reports/', views.list_reports, name='list_reports'),
    path('api/download_report/<str:filename>/', views.download_report, name='download_report'),
    
    # Hardware Hash Protection endpoints
    path('api/hardware-hash/generate/', views.generate_hardware_hash, name='generate_hardware_hash'),
    path('api/hardware-hash/analyze/', views.analyze_hardware_hash, name='analyze_hardware_hash'),
    path('api/download_hardware_hash/<str:filename>/', views.download_hardware_hash, name='download_hardware_hash'),
    
    # MCP Task Execution endpoints (AutoGen Integration)
    path('api/mcp/execute/', mcp_views.execute_mcp_tasks, name='execute_mcp_tasks'),
    path('api/mcp/parse/', mcp_views.parse_mcp_tasks, name='parse_mcp_tasks'),
    path('api/mcp/status/', mcp_views.get_orchestrator_status, name='orchestrator_status'),
    
    # Conversation Management endpoints
    path('api/conversations/', conversation_views.list_conversations, name='list_conversations'),
    path('api/conversations/create/', conversation_views.create_conversation, name='create_conversation'),
    path('api/conversations/<uuid:conversation_id>/', conversation_views.get_conversation, name='get_conversation'),
    path('api/conversations/<uuid:conversation_id>/update/', conversation_views.update_conversation, name='update_conversation'),
    path('api/conversations/<uuid:conversation_id>/delete/', conversation_views.delete_conversation, name='delete_conversation'),
    path('api/conversations/<uuid:conversation_id>/messages/', conversation_views.add_message, name='add_message'),
    path('api/conversations/save-bulk/', conversation_views.save_conversation_bulk, name='save_conversation_bulk'),
    
    # Service Centers endpoint
    path('api/service-centers/nearby/', views.get_nearby_service_centers, name='get_nearby_service_centers'),
    
    # PC Compatibility Checker endpoints
    path('api/compatibility/scan/', views.scan_hardware_specs, name='scan_hardware_specs'),
    path('api/compatibility/check/', views.check_upgrade_compatibility, name='check_upgrade_compatibility'),
    path('api/compatibility/recommendations/', views.get_upgrade_recommendations, name='get_upgrade_recommendations'),
]
