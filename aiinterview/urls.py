from django.urls import path
from . import views

urlpatterns = [
    path('start-interview/', views.start_interview, name='start_interview'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('next-question/', views.next_question, name='next_question'),
    path('interview-results/<int:interview_id>/', views.get_results, name='interview_results'),
    path('enhance-text/', views.enhance_text, name='enhance_text'),
]
