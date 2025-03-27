from rest_framework import serializers
from .models import QuestionHistory, Exam

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['id', 'start_time', 'completed', 'score']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionHistory
        fields = ['id', 'question', 'options']

class QuestionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionHistory
        fields = '__all__'
