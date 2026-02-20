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
from driver.serializers import *
from driver.models import Driver
from company.models import Company
from company.serializers import *
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
reset_token_generator = PasswordResetTokenGenerator()

def _jwt_for_user(user: User):
    refresh = RefreshToken.for_user(user)
    return {"status": "success","access_token": str(refresh.access_token)}




class SignupView(APIView):
    permission_classes = [AllowAny]
    @transaction.atomic
    def post(self, request):
        try:
            role = request.data.get("role")
            if role not in ["customer", "driver", "company", "admin"]:
                return Response({"status": "error", "message": "Invalid role."},status=status.HTTP_400_BAD_REQUEST)
            if role == "customer":
                ser = UserSignupSerializer(data=request.data)
            elif role == "driver":
                ser = DriverSignupSerializer(data=request.data)
            elif role == "company":
                ser = CompanySignupSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            user = ser.save()
            if getattr(user, "email_verified", False) is False and user.is_active is True:
                user.is_active = False
                user.save(update_fields=["is_active"])
            EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)
            sent_email, otp_code = send_otp(user)
            if not sent_email:
                return Response(
                    {"status": "error", "message": "Could not send OTP. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            EmailOTP.objects.create(user=user, code_hash=otp_code, expires_at=timezone.now() + timezone.timedelta(minutes=10))
            return Response(
                {
                    "status": "success",
                    "message": "Account created successfully. OTP sent to your email."
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


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
        try:
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
        except Exception as e:
            return Response({"status":"error","message": str(e)}, status=400)





class VerifyEmail(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
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
            token =  str(refresh.access_token)
            return Response({"status": "success","message": "Email verified successfully.", "access_token": token}, status=200)
        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=400)





class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
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
        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=400)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            ser = ChangePasswordSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            user = request.user
            if not user.check_password(ser.validated_data["old_password"]):
                return Response({"status": "error","detail": "Old password is incorrect."}, status=400)
            user.set_password(ser.validated_data["new_password"])
            user.save(update_fields=["password"])
            return Response({"status": "success","message": "Password changed successfully."})
        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=400)



class SendPhoneOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
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
        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
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
                user.is_active = True
                user.phone_verified = True
                user.phone_verified_at = timezone.now()
                user.save(update_fields=["phone_verified", "phone_verified_at","is_active"])
            refresh = RefreshToken.for_user(user)
            access_token =  refresh.access_token
            return Response({"status": "success","message": "Phone verified successfully.", "access_token": access_token}, status=200)
        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=400)





class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user = request.user
        try:
            if user.role == "customer" or user.role == "admin":
                return Response({
                    "status": "success",
                    "data":UserProfileSerializer(request.user).data})
            elif user.role == "driver":
                driver = get_object_or_404(Driver, user_id=user.user_id)
                return Response({
                    "status": "success",
                    "data":DriverProfileSerializer(driver).data})
            elif user.role == "company":
                company = get_object_or_404(Company, user_id=user.user_id)
                return Response({
                    "status": "success",
                    "data":CompanyProfileSerializer(company).data})

        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

    def patch(self, request):
        try:
            user = request.user
            if user.role == "customer" or user.role == "admin":
                user_ser = UserProfileSerializer(user, data=request.data, partial=True)
                user_ser.is_valid(raise_exception=True)
                user_ser.save()
                return Response({
                    "status": "success",
                    "message": "Driver profile updated successfully.",
                    "data": UserProfileSerializer(user).data
                }, status=status.HTTP_200_OK)
            elif user.role == "driver":
                driver = get_object_or_404(Driver, user_id=user.user_id)
                user_ser = DriverUpdateSerializer(driver, data=request.data, partial=True)
                user_ser.is_valid(raise_exception=True)
                user_ser.save()
                return Response({
                    "status": "success",
                    "message": "Driver profile updated successfully.",
                    "data": DriverUpdateSerializer(driver).data
                }, status=status.HTTP_200_OK)
            elif user.role == "company":
                company = get_object_or_404(Company, user_id=user.user_id)
                user_ser = CompanyUpdateSerializer(company, data=request.data, partial=True)
                user_ser.is_valid(raise_exception=True)
                user_ser.save()
                return Response({
                    "status": "success",
                    "message": "Company profile updated successfully.",
                    "data": CompanyUpdateSerializer(company).data
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "error", "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

    def delete(self, request):
        try:
            request.user.delete()
            return Response({"status": "success","message": "Account deleted successfully."})
        except Exception as e:
            return Response({"status": "error","detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
