from django.db import models
from django.contrib.auth.models import User
import uuid

class Exam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)

    class Meta:
        ordering = ['-start_time']

class QuestionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    options = models.JSONField()
    correct_answer = models.CharField(max_length=255)
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')

    class Meta:
        ordering = ['-created_at']
