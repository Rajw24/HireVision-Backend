from django.urls import path
from . import views

urlpatterns = [
    path('history/', views.get_user_history, name='get_user_history'),
    path('start-exam/', views.start_exam, name='start_exam'),
    path('submit-exam/', views.submit_exam, name='submit_exam'),
    path('exam-history/', views.get_exam_history, name='get_exam_history'),
    path('exam-details/<int:exam_id>/', views.get_exam_details, name='get_exam_details'),
]
