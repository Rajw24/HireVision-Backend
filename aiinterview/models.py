from django.db import models
from django.contrib.auth.models import User
import os
from django.conf import settings

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return os.path.join(settings.MEDIA_ROOT, f'user_{instance.user}/resume', filename)


class Interview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews')
    candidate_name = models.CharField(max_length=100)
    resume_content = models.TextField()
    resume_file = models.FileField(upload_to=user_directory_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

class Responses(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='responses')
    question = models.TextField()
    answer = models.TextField()
    question_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class Result(models.Model):
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='result')
    # Technical scores
    technical_accuracy = models.FloatField(default=0.0)
    depth_of_knowledge = models.FloatField(default=0.0)
    relevance_score = models.FloatField(default=0.0)
    
    # Language quality scores
    grammar_score = models.FloatField(default=0.0)
    clarity_score = models.FloatField(default=0.0)
    professionalism_score = models.FloatField(default=0.0)
    
    # Sentiment scores
    positive_sentiment = models.FloatField(default=0.0)
    neutral_sentiment = models.FloatField(default=0.0)
    negative_sentiment = models.FloatField(default=0.0)
    compound_sentiment = models.FloatField(default=0.0)
    
    # Overall scores
    overall_technical_score = models.FloatField(default=0.0)
    overall_communication_score = models.FloatField(default=0.0)
    final_score = models.FloatField(default=0.0)
    
    # Feedback fields
    technical_feedback = models.TextField(blank=True, default='')
    communication_feedback = models.TextField(blank=True, default='')
    strengths = models.JSONField(default=list)
    areas_for_improvement = models.JSONField(default=dict)
    vocabulary_analysis = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
