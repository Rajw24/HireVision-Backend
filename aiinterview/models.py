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
    accuracy_score = models.FloatField()
    fluency_score = models.FloatField()
    rhythm_score = models.FloatField()
    overall_score = models.FloatField()
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
