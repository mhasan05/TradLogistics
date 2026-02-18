from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from utils.common import get_twilio_client
from .serializers import SendPhoneOTPSerializer, VerifyPhoneOTPSerializer
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from utils.common import send_otp
from .models import User, EmailOTP
from .serializers import *
from django.contrib.auth.tokens import PasswordResetTokenGenerator


from .serializers import SendEmailOTPSerializer, VerifyEmailOTPSerializer

reset_token_generator = PasswordResetTokenGenerator()

def _jwt_for_user(user: User):
    refresh = RefreshToken.for_user(user)
    return {"status": "success","access_token": str(refresh.access_token)}




class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            ser = SignupSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            user = ser.save()
            sent_email,otp = send_otp(user)
            if not sent_email:
                    return Response({"status": "error", "message": "Something went wrong, please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            EmailOTP.objects.create(user=user, code_hash=otp, expires_at=timezone.now() + timezone.timedelta(minutes=10))
            return Response({"status": "success", "message": "Account created successfully. Please verify your email."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            ser = LoginSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            user = ser.validated_data["user"]
            return Response(_jwt_for_user(user))
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class SentEmailOTP(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"status":"error","message": "User not found."}, status=404)
        sent_email, otp = send_otp(user)
        if not sent_email:
            return Response({"status":"error","message": "Something went wrong, please try again later."}, status=500)
        EmailOTP.objects.create(user=user, code_hash=otp, expires_at=timezone.now() + timezone.timedelta(minutes=10))
        return Response({"status":"success","message": "OTP sent to your email for password reset."}, status=200)





class VerifyEmail(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        user = get_object_or_404(User, email=email)
        get_otp = EmailOTP.objects.filter(user=user, code_hash=otp, is_used=False).first()
        if not get_otp:
            return Response({"status": "error","detail": "Invalid or expired OTP."}, status=400)
        if get_otp.expires_at < timezone.now():
            return Response({"status": "error","detail": "OTP has expired."}, status=400)
        user.is_active = True
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["is_active"])
        get_otp.is_used = True
        get_otp.save(update_fields=["is_used"])
        refresh = RefreshToken.for_user(user)
        access_token =  refresh.access_token
        return Response({"status": "success","message": "Email verified successfully.", "access_token": access_token}, status=200)





class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = request.user
        new_password = ser.validated_data["new_password"]
        confirm_password = ser.validated_data["confirm_password"]

        if not new_password == confirm_password:
            return Response({"status": "error","detail": "Passwords do not match."}, status=400)

        user.set_password(ser.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"status": "success","message": "Password reset successful."})

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(ser.validated_data["old_password"]):
            return Response({"status": "error","detail": "Old password is incorrect."}, status=400)
        user.set_password(ser.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"status": "success","message": "Password changed successfully."})



class SendPhoneOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = SendPhoneOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        phone = ser.validated_data["phone"]
        channel = ser.validated_data["channel"]

        client = get_twilio_client()
        client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=phone,
            channel=channel,
        )

        return Response({"status": "success","message": "OTP sent."}, status=status.HTTP_200_OK)


class VerifyPhoneOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = VerifyPhoneOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        phone = ser.validated_data["phone"]
        code = ser.validated_data["code"]

        client = get_twilio_client()
        check = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone,
            code=code,
        )

        # Twilio returns status like: "approved" when correct
        if check.status != "approved":
            return Response({"status": "error","detail": "Invalid or expired OTP."}, status=400)

        # Mark verified (if user exists)
        user = User.objects.filter(phone=phone).first()
        if user:
            user.phone_verified = True
            user.phone_verified_at = timezone.now()
            user.save(update_fields=["phone_verified", "phone_verified_at"])
        refresh = RefreshToken.for_user(user)
        access_token =  refresh.access_token
        return Response({"status": "success","message": "Phone verified successfully.", "access_token": access_token}, status=200)





class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "status": "success",
            "data":UserProfileSerializer(request.user).data})
    

    def patch(self, request):
        ser = UserProfileSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"status": "success","message": "Profile updated successfully.","data":UserProfileSerializer(request.user).data})
    

    def delete(self, request):
        request.user.delete()
        return Response({"status": "success","message": "Account deleted successfully."})
    
