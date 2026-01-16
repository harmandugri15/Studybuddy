from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signin/', views.signin, name='signin'),
    path('vault/', views.notes_hub, name='notes_hub'),
    path('syllabus/', views.topics_hub, name='topics_hub'),
    path('datesheet/', views.datesheet_hub, name='datesheet_hub'), # NEW URL
    
    # Actions
    path('delete_note/<int:note_id>/', views.delete_note, name='delete_note'),
    path('rename_note/<int:note_id>/', views.rename_note, name='rename_note'),
    path('delete_mission/<int:exam_id>/', views.delete_mission, name='delete_mission'),
    path('rename_topic/<int:topic_id>/', views.rename_topic, name='rename_topic'),
    path('rename_mission/<int:exam_id>/', views.rename_exam, name='rename_exam'),
    path('delete_exam/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    path('clear_datesheet/', views.clear_datesheet, name='clear_datesheet'),
    path('squads/', views.squad_hub, name='squad_hub'),
    # NEW LINE:
    path('squads/<int:squad_id>/', views.squad_detail, name='squad_detail'),
    # NEW LINE for the pulse
    path('squads/<int:squad_id>/messages/', views.get_squad_messages, name='get_squad_messages'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)