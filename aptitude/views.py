import asyncio
import aiohttp
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
import requests
from .models import QuestionHistory, Exam
from .serializers import QuestionSerializer, QuestionHistorySerializer, ExamSerializer

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_history(request):
    history = QuestionHistory.objects.filter(user=request.user)
    serializer = QuestionHistorySerializer(history, many=True)
    return Response(serializer.data)

async def fetch_question(session, category_id):
    url = f'https://aptitude-api.vercel.app/{category_id}'
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
    return None

async def fetch_questions(category_id, num_questions=20):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_question(session, category_id) for _ in range(num_questions)]
        results = await asyncio.gather(*tasks)
        # Filter out None values and ensure uniqueness based on question text
        unique_questions = []
        seen_questions = set()
        for result in results:
            if result and result['question'] not in seen_questions:
                seen_questions.add(result['question'])
                unique_questions.append(result)
                if len(unique_questions) >= 15:
                    break
        return unique_questions[:15]

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_exam(request):
    exam = Exam.objects.create(user=request.user)
    questions = []
    category_id = request.data.get('category_id', 'Random')

    # Run async code in sync context
    question_data = asyncio.run(fetch_questions(category_id))
    
    for data in question_data:
        question = QuestionHistory.objects.create(
            user=request.user,
            exam=exam,
            question=data['question'],
            options=data['options'],
            correct_answer=data['answer'],
            explanation=data['explanation']
        )
        questions.append({
            'id': question.id,
            'question': data['question'],
            'options': data['options']
        })
    
    return Response({
        'exam_id': exam.id,
        'questions': questions
    })

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_exam(request):
    exam_id = request.data.get('exam_id')
    answers = request.data.get('answers', [])  # List of {question_id: answer}
    
    try:
        exam = Exam.objects.get(id=exam_id, user=request.user)
        if exam.completed:
            return Response({'error': 'Exam already submitted'}, status=400)
        
        correct_count = 0
        for answer in answers:
            question = QuestionHistory.objects.get(
                id=answer['question_id'],
                exam=exam,
                user=request.user
            )
            # Compare answers only if user provided an answer
            if answer['answer'] is not None and answer['answer'] == question.correct_answer:
                correct_count += 1
        
        exam.score = correct_count
        exam.completed = True
        exam.save()
        
        return Response({
            'score': correct_count,
            'total': len(answers)
        })
    except Exam.DoesNotExist:
        return Response({'error': 'Exam not found'}, status=404)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exam_history(request):
    exams = Exam.objects.filter(user=request.user)
    serializer = ExamSerializer(exams, many=True)
    return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exam_details(request, exam_id):
    try:
        exam = Exam.objects.get(id=exam_id, user=request.user)
        questions = QuestionHistory.objects.filter(exam=exam)
        return Response({
            'exam': ExamSerializer(exam).data,
            'questions': QuestionHistorySerializer(questions, many=True).data
        })
    except Exam.DoesNotExist:
        return Response({'error': 'Exam not found'}, status=404)
