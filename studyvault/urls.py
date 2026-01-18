from django.contrib import admin
from django.urls import path, include
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('vault/', views.notes_hub, name='notes_hub'),
    path('syllabus/', views.topics_hub, name='topics_hub'),
    path('datesheet/', views.datesheet_hub, name='datesheet_hub'),
    
    # Core Actions
    path('delete_note/<int:note_id>/', views.delete_note, name='delete_note'),
    path('rename_note/<int:note_id>/', views.rename_note, name='rename_note'),
    path('delete_mission/<int:exam_id>/', views.delete_mission, name='delete_mission'),
    path('rename_topic/<int:topic_id>/', views.rename_topic, name='rename_topic'),
    path('rename_mission/<int:exam_id>/', views.rename_exam, name='rename_exam'),
    path('delete_exam/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    path('clear_datesheet/', views.clear_datesheet, name='clear_datesheet'),
    
    # Squads
    path('squads/', views.squad_hub, name='squad_hub'),
    path('squads/<int:squad_id>/', views.squad_detail, name='squad_detail'),
    path('squads/<int:squad_id>/messages/', views.get_squad_messages, name='get_squad_messages'),
    
    # NEW: Refresh-Free Logic & Delete Topic
    path('api/toggle-topic/', views.toggle_topic_status, name='toggle_topic_status'),
    path('syllabus/delete/<int:topic_id>/', views.delete_topic, name='delete_topic'),
    path('api/vault-chat/', views.vault_chat, name='vault_chat'),

    # Auth
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)