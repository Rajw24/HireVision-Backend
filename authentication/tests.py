from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

class AuthViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            is_active=False
        )
        self.user.token_created_at = timezone.now()
        self.user.save()

    def test_signup(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password': 'password123',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Signup successful', response.json()['message'])

    def test_email_verification(self):
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('email_verification', args=[uid, token]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Email verified successfully', response.json()['message'])

    def test_resend_verification_link(self):
        response = self.client.post(reverse('resend_verification_link'), {
            'email': 'testuser@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Verification link resent', response.json()['message'])

    def test_signin(self):
        self.user.is_active = True
        self.user.save()
        response = self.client.post(reverse('signin'), {
            'email': 'testuser@example.com',
            'password': 'password123',
            'remember_me': 'true'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json())
        self.assertIn('user', response.json())
        self.assertIn('tokens', response.json())
        
        user_data = response.json()['user']
        self.assertEqual(user_data['email'], 'testuser@example.com')
        self.assertEqual(user_data['username'], 'testuser')
        self.assertIn('id', user_data)
        self.assertIn('first_name', user_data)
        self.assertIn('last_name', user_data)
        self.assertIn('is_active', user_data)

    def test_signout(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('signout'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Signout successful', response.json()['message'])

    def test_change_password(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('change_password'), {
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Password changed successfully', response.json()['message'])

    def test_forgot_password(self):
        response = self.client.post(reverse('forgot_password'), {
            'email': 'testuser@example.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Password reset email sent', response.json()['message'])

    def test_reset_password(self):
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.post(reverse('reset_password', args=[uid, token]), {
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Password reset successfully', response.json()['message'])

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_active=True
        )
        self.signin_url = reverse('signin')
        self.signout_url = reverse('signout')

    def test_signin_success(self):
        response = self.client.post(self.signin_url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(response.cookies.get('access_token'))
        self.assertTrue(response.cookies.get('refresh_token'))

    def test_signin_rate_limit(self):
        for _ in range(6):
            response = self.client.post(self.signin_url, {
                'email': 'test@example.com',
                'password': 'wrong'
            })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_signout(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.client.cookies['refresh_token'] = str(refresh)
        
        response = self.client.post(self.signout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('refresh_token', response.cookies)
        self.assertNotIn('access_token', response.cookies)
