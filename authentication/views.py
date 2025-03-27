from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from datetime import timedelta
from django.db import models
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
from .throttling import AuthenticationThrottle
from rest_framework.decorators import throttle_classes
import logging
from .serializers import UserSerializer
from django.http import HttpResponse

logger = logging.getLogger(__name__)

# Add a field to store token creation time
User.add_to_class('token_created_at', models.DateTimeField(null=True, blank=True))

# Create your views here.
# @api_view(['GET'])
# def get_csrf_token(request):
#     return Response({'message': 'CSRF token set.'})

@api_view(['POST'])
@csrf_exempt
def signup(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')

    if not username or not password or not email:
        return Response({'error': 'Username, password, and email are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=False  # User is inactive until email is verified
    )

    # Store token creation time
    user.token_created_at = timezone.now()
    user.save()

    # Send verification email
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verification_link = request.build_absolute_uri(f'/auth/email-verification/{uid}/{token}/')
    email_subject = 'Verify your email address'
    email_body = render_to_string('email_verification.html', {
        'user': user,
        'verification_link': verification_link
    })
    send_mail(email_subject, email_body, 'noreply@hirevision.com', [email])

    return Response({'message': 'Signup successful. Please verify your email.'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def email_verification(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        token_age = timezone.now() - user.token_created_at
        if token_age < timedelta(minutes=10):
            user.is_active = True
            user.save()
            return render(request, 'verification_success.html')
        else:
            return render(request, 'verification_expired.html', status=400)
    else:
        return render(request, 'verification_invalid.html', status=400)

@api_view(['POST'])
@csrf_exempt
def resend_verification_link(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_active:
        return Response({'message': 'This account is already verified.'}, status=status.HTTP_400_BAD_REQUEST)

    # Resend verification email
    user.token_created_at = timezone.now()
    user.save()
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verification_link = request.build_absolute_uri(f'/auth/email-verification/{uid}/{token}/')
    email_subject = 'Verify your email address'
    email_body = render_to_string('email_verification.html', {
        'user': user,
        'verification_link': verification_link
    })
    send_mail(email_subject, email_body, 'noreply@hirevision.com', [email])

    return Response({'message': 'Verification link resent. Please check your email.'}, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['POST', 'OPTIONS'])
@throttle_classes([AuthenticationThrottle])
def signin(request):
    # Handle OPTIONS request explicitly
    if request.method == 'OPTIONS':
        response = Response()
        response['Allow'] = 'POST, OPTIONS'
        return response
        
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        remember_me = request.data.get('remember_me') == 'true'

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Failed login attempt for non-existent email: {email}")
            return Response(
                {'error': 'Invalid credentials.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = authenticate(username=user.username, password=password)
        if user is not None and user.is_active:
            refresh = RefreshToken.for_user(user)
            user_serializer = UserSerializer(user)
            
            response = Response({
                'message': 'Signin successful.',
                'user': user_serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

            # Set secure cookies
            response.set_cookie(
                'refresh_token',
                str(refresh),
                max_age=2592000 if remember_me else 3600,
                httponly=True,
                secure=False,  # Allow HTTP
                samesite='Lax'  # Changed from Strict for HTTP
            )
            response.set_cookie(
                'access_token',
                str(refresh.access_token),
                max_age=900,  # 15 minutes
                httponly=True,
                secure=False,  # Allow HTTP
                samesite='Lax'  # Changed from Strict for HTTP
            )
            logger.info(f"Successful login for user: {user.email}")
            return response

        logger.warning(f"Failed login attempt for email: {email}")
        return Response(
            {'error': 'Invalid credentials.'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            {'error': 'An error occurred during signin.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@csrf_exempt
def signout(request):
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if (refresh_token):
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"User signed out successfully")
    except TokenError:
        logger.warning(f"Invalid token during signout for user: {request.user.email}")
        return Response(
            {'error': 'Invalid token.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Signout error: {str(e)}")
        return Response(
            {'error': 'An error occurred during signout.'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    logout(request)
    response = Response({'message': 'Signout successful.'}, status=status.HTTP_200_OK)
    response.delete_cookie('refresh_token')
    response.delete_cookie('access_token')
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def change_password(request):
    user = request.user
    last_login = user.last_login
    current_time = timezone.now()

    # Check if the user has been inactive for more than 30 days
    if current_time - last_login > timedelta(days=30):
        return Response({'error': 'You have been inactive for too long. Please login again to change your password.'}, status=status.HTTP_400_BAD_REQUEST)

    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')

    if not new_password or not confirm_password:
        return Response({'error': 'New password and confirm password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if new_password != confirm_password:
        return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@csrf_exempt
def forgot_password(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate password reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = request.build_absolute_uri(f'/auth/reset-password/{uid}/{token}/')
    email_subject = 'Reset your password'
    email_body = render_to_string('password_reset_email.html', {
        'user': user,
        'reset_link': reset_link
    })
    send_mail(email_subject, email_body, 'noreply@hirevision.com', [email])

    return Response({'message': 'Password reset email sent. Please check your email.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@csrf_exempt
def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not new_password or not confirm_password:
            return Response({'error': 'New password and confirm password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)