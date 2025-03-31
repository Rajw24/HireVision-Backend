from django.shortcuts import render
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http.request import QueryDict
from .models import Interview, Responses, Result  # Updated import
from .interviewAgent import ResumeInterviewAgent
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FileUploadParser, MultiPartParser, FormParser, JSONParser
import json 
import base64
import tempfile
import os

def validate_resume_data(data):
    """Validate the resume data from request"""
    if not isinstance(data, (dict, QueryDict)):
        return False, "Invalid request format"
    
    resume = data.get('resume')
    if not resume:
        return False, "Resume is required"
    
    # Handle invalid formats
    if isinstance(resume, (dict, list)) or resume == '[object Object]':
        return False, "Invalid resume data format"
    
    try:
        # Decode base64 string
        resume_bytes = base64.b64decode(str(resume).strip())
        if not resume_bytes.startswith(b'%PDF'):
            return False, "Invalid PDF format"
        return True, resume_bytes
    except Exception as e:
        return False, f"Invalid base64 encoding: {str(e)}"
agent = None
def get_or_create_agent(request, interview_id=None):
    """Helper function to get or create interview agent"""
    global agent
    if agent is None:
        agent = ResumeInterviewAgent(
            settings.GROQ_API_KEY, 
            user_name=request.user.first_name,
            interview_id=interview_id
        )
        request.session['agent_created'] = True
    return agent

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])  # Added JSONParser
def start_interview(request):
    """Start a new interview session"""
    if request.method == 'POST':
        try:
            # Get interview_id from request data
            interview_id = request.data.get('interview_id')
            
            # Initialize agent
            agent = get_or_create_agent(request)
            
            try:
                if interview_id:
                    # Try to get existing interview
                    interview = Interview.objects.get(
                        id=interview_id,
                        user=request.user,
                        completed=False
                    )
                else:
                    # Create new interview if no ID provided
                    interview = Interview.objects.create(
                        user=request.user,
                        candidate_name=f"{request.user.first_name} {request.user.last_name}",
                        # resume_content="resume_content",
                    )
            except Interview.DoesNotExist:
                return Response({
                    'error': 'Interview not found',
                    'details': 'Invalid interview_id'
                }, status=404)
            
            # Generate first question
            first_question = agent.generate_question()
            Responses.objects.create(
                interview=interview,
                question=first_question,
                question_number=1
            )
            
            # Store interview_id in session
            request.session['current_interview_id'] = interview.id
            
            return Response({
                'status': 'success',
                'interview_id': interview.id,
                'question': first_question,
                'question_number': 1
            })
                
        except Exception as e:
            print("Error in start_interview:", str(e))
            return Response({
                'error': 'Interview initialization failed',
                'details': str(e)
            }, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_resume(request):
    """Handle resume upload"""
    if 'resume' not in request.FILES:
        return Response({
            'error': 'Missing file',
            'details': 'Resume file is required'
        }, status=400)
        
    resume_file = request.FILES['resume']
    if not resume_file.name.endswith('.pdf'):
        return Response({
            'error': 'Invalid file',
            'details': 'File must be a PDF'
        }, status=400)
        
    try:
        # Store resume temporarily or permanently as needed
        # For now, we'll just return success

        interview = Interview.objects.create(
                user=request.user,
                candidate_name=f"{request.user.first_name} {request.user.last_name}",
                # resume_content="resume_content",  
                resume_file=resume_file # Save the actual file
            )

        return Response({
            'status': 'success',
            'message': 'Resume uploaded successfully',
            'interview_id': interview.id
        })
    except Exception as e:
        return Response({
            'error': 'Upload failed',
            'details': str(e)
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def next_question(request):
    if request.method == 'POST':
        try:
            print("IN next-question")
            interview_id = request.data.get('interview_id')
            answer = request.data.get('answer')
            print("Got iid and ans",interview_id, answer)
            # Validate required fields
            if not interview_id:
                return Response({
                    'error': 'Missing interview_id',
                    'details': 'interview_id is required'
                }, status=400)
            
            if not answer:
                return Response({
                    'error': 'Missing answer',
                    'details': 'answer is required'
                }, status=400)
            
            try:
                print("Getting INterview")
                interview = Interview.objects.get(id=interview_id, user=request.user)
                print("Getting INterview done")
            except Interview.DoesNotExist:
                print("Getting INterview failed")
                return Response({
                    'error': 'Interview not found',
                    'details': 'Invalid interview_id or unauthorized access'
                }, status=404)
            
            print("fetching c q")
            current_question = interview.responses.last()
            print("fetching c q done")
            if not current_question:
                print("fetching c q error")
                return Response({
                    'error': 'Invalid interview state',
                    'details': 'No questions found for this interview'
                }, status=400)
            
            # Use the same agent or create if doesn't exist
            print("Getting agent")
            agent = get_or_create_agent(request, interview_id)
            print("Getting agent done")
            
            # Load resume content automatically
            # agent.load_resume_from_interview()
            
            # Load interview context
            print("Loading prs")
            previous_responses = interview.responses.all().order_by('question_number')
            for response in previous_responses:
                if response.answer:
                    agent.memory.save_context(
                        {"input": response.question},
                        {"output": response.answer}
                    )
            
            print("Loading prs done")
            # Save answer
            current_question.answer = answer
            current_question.save()
            
            if current_question.question_number >= 10:
                # Generate final results
                try:
                    responses_data = [{
                        'question_number': r.question_number,
                        'question': r.question,
                        'answer': r.answer
                    } for r in interview.responses.all()]
                    
                    # Generate scores
                    accuracy = 0.75
                    fluency = 0.75
                    rhythm = 0.75
                    overall = (accuracy + fluency + rhythm) / 3
                    
                    result = Result.objects.create(
                        interview=interview,
                        accuracy_score=accuracy,
                        fluency_score=fluency,
                        rhythm_score=rhythm,
                        overall_score=overall,
                        feedback=agent.generate_feedback(responses_data)
                    )
                    
                    interview.completed = True
                    interview.save()
                    
                    return Response({
                        'status': 'completed',
                        'result_id': result.id
                    })
                except Exception as e:
                    return Response({
                        'error': 'Failed to generate results',
                        'details': str(e)
                    }, status=500)
            
            # Generate next question
            try:
                print("Generating next question")
                next_question = agent.generate_question(answer)
                new_response = Responses.objects.create(
                    interview=interview,
                    question=next_question,
                    question_number=current_question.question_number + 1
                )
                
                print("Generating next question done")
                return Response({
                    'status': 'success',
                    'question': next_question,
                    'question_number': new_response.question_number
                })
            except Exception as e:
                print("Generating next question failed")
                print(e)
                return Response({
                    'error': 'Failed to generate next question',
                    'details': str(e)
                }, status=500)
                
        except json.JSONDecodeError:
            return Response({
                'error': 'Invalid JSON format',
                'details': 'Request body must be valid JSON'
            }, status=400)
        except Exception as e:
            return Response({
                'error': 'Unexpected error',
                'details': str(e)
            }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_results(request, interview_id):
    try:
        interview = Interview.objects.get(id=interview_id, user=request.user)
        result = interview.result
        
        return Response({
            'candidate_name': interview.candidate_name,
            'scores': {
                'accuracy': result.accuracy_score,
                'fluency': result.fluency_score,
                'rhythm': result.rhythm_score,
                'overall': result.overall_score
            },
            'feedback': result.feedback,
            'responses': [{
                'question': r.question,
                'answer': r.answer
            } for r in interview.responses.all()]
        })
    except Interview.DoesNotExist:
        return Response({'error': 'Interview not found or unauthorized'}, status=404)
