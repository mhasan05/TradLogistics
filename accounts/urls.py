from django.urls import path
from .views import *

urlpatterns = [
    path("signup/", SignupView.as_view()),
    path("login/", LoginView.as_view()),

    path("email/send-otp/", SentEmailOTP.as_view()),
    path("email/verify-email/", VerifyEmail.as_view()),
    

    path("reset-password/", ResetPasswordView.as_view()),
    path("change-password/", ChangePasswordView.as_view()),

    path("phone/send-otp/", SendPhoneOTPView.as_view()),
    path("phone/verify-otp/", VerifyPhoneOTPView.as_view()),


    path("profile/", MyProfileView.as_view()),
]
