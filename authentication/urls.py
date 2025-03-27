from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('email-verification/<uidb64>/<token>/', views.email_verification, name='email_verification'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('resend-verification-link/', views.resend_verification_link, name='resend_verification_link'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    # path('get-csrf-token/', views.get_csrf_token, name='get_csrf_token'),
    # path('verify-token/', views.verify_token, name='verify_token'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
