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
            interview_id = request.data.get('interview_id')
            answer = request.data.get('answer')
            
            if not interview_id or not answer:
                return Response({
                    'error': 'Missing required fields',
                    'details': 'interview_id and answer are required'
                }, status=400)
            
            try:
                interview = Interview.objects.get(id=interview_id, user=request.user)
            except Interview.DoesNotExist:
                return Response({
                    'error': 'Interview not found',
                    'details': 'Invalid interview_id or unauthorized access'
                }, status=404)
            
            current_question = interview.responses.last()
            if not current_question:
                return Response({
                    'error': 'Invalid interview state',
                    'details': 'No questions found for this interview'
                }, status=400)
            
            # Save the current answer
            current_question.answer = answer
            current_question.save()
            
            if current_question.question_number >= 10:
                # This is the last question - generate analysis
                try:
                    # Create a temporary CSV file with interview data
                    import pandas as pd
                    import tempfile
                    import os
                    
                    responses_data = [{
                        'question_number': r.question_number,
                        'question': r.question,
                        'answer': r.answer
                    } for r in interview.responses.all()]
                    
                    df = pd.DataFrame(responses_data)
                    
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
                        df.to_csv(tmp.name, index=False)
                        tmp_path = tmp.name
                    
                    # Initialize analyzer and process interview
                    from .analyzerAgent import InterviewAnalyzer
                    analyzer = InterviewAnalyzer(settings.GROQ_API_KEY)
                    analyzer.load_interview_data(tmp_path)
                    
                    # Run all analyses
                    analyzer.analyze_sentiment()
                    analyzer.analyze_vocabulary()
                    analyzer.analyze_grammar()
                    analyzer.analyze_technical_content()
                    
                    # Generate visualizations
                    analyzer.visualize_results()
                    
                    # Get JSON formatted results
                    analysis_results = analyzer.generate_analysis_json()
                    
                    # Create result object
                    result = Result.objects.create(
                        interview=interview,
                        technical_accuracy=analysis_results['technical_accuracy'],
                        depth_of_knowledge=analysis_results['depth_of_knowledge'],
                        relevance_score=analysis_results['relevance_score'],
                        grammar_score=analysis_results['grammar_score'],
                        clarity_score=analysis_results['clarity_score'],
                        professionalism_score=analysis_results['professionalism_score'],
                        positive_sentiment=analysis_results['positive_sentiment'],
                        neutral_sentiment=analysis_results['neutral_sentiment'],
                        negative_sentiment=analysis_results['negative_sentiment'],
                        compound_sentiment=analysis_results['compound_sentiment'],
                        overall_technical_score=analysis_results['overall_technical_score'],
                        overall_communication_score=analysis_results['overall_communication_score'],
                        final_score=analysis_results['final_score'],
                        technical_feedback=analysis_results['technical_feedback'],
                        communication_feedback=analysis_results['communication_feedback'],
                        strengths=analysis_results['strengths'],
                        areas_for_improvement=analysis_results['areas_for_improvement'],
                        vocabulary_analysis=analysis_results['vocabulary_analysis']
                    )
                    
                    # Clean up temporary file
                    os.unlink(tmp_path)
                    
                    # Mark interview as completed
                    interview.completed = True
                    interview.save()
                    
                    # Return result
                    return Response({
                        'status': 'completed',
                        'result_id': result.id,
                        'analysis': analysis_results
                    })
                    
                except Exception as e:
                    print("Error in analysis:", str(e))
                    return Response({
                        'error': 'Failed to generate results',
                        'details': str(e)
                    }, status=500)
            
            # Not the last question, generate next question
            agent = get_or_create_agent(request, interview_id)
            try:
                next_question = agent.generate_question(answer)
                new_response = Responses.objects.create(
                    interview=interview,
                    question=next_question,
                    question_number=current_question.question_number + 1
                )
                
                return Response({
                    'status': 'success',
                    'question': next_question,
                    'question_number': new_response.question_number
                })
            except Exception as e:
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
            'technical_scores': {
                'technical_accuracy': result.technical_accuracy,
                'depth_of_knowledge': result.depth_of_knowledge,
                'relevance_score': result.relevance_score,
                'overall_technical_score': result.overall_technical_score
            },
            'communication_scores': {
                'grammar_score': result.grammar_score,
                'clarity_score': result.clarity_score,
                'professionalism_score': result.professionalism_score,
                'overall_communication_score': result.overall_communication_score
            },
            'sentiment_scores': {
                'positive': result.positive_sentiment,
                'neutral': result.neutral_sentiment,
                'negative': result.negative_sentiment,
                'compound': result.compound_sentiment
            },
            'final_score': result.final_score,
            'feedback': {
                'technical_feedback': result.technical_feedback,
                'communication_feedback': result.communication_feedback,
                'strengths': result.strengths,
                'areas_for_improvement': result.areas_for_improvement,
                'vocabulary_analysis': result.vocabulary_analysis
            },
            'responses': [{
                'question': r.question,
                'answer': r.answer
            } for r in interview.responses.all()]
        })
    except Interview.DoesNotExist:
        return Response({'error': 'Interview not found or unauthorized'}, status=404)
