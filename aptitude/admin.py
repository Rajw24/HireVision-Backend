from django.contrib import admin
from .models import QuestionHistory, Exam
# Register your models here.

admin.site.register(QuestionHistory)
admin.site.register(Exam)