from rest_framework import viewsets
from .models import User
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .send_otp import send_otp
import random
import string
from datetime import timedelta
from .models import UserPickupLocation
from geopy.geocoders import Nominatim
from django.db.models import Q



class LoginView(APIView):
    """
    Handle user login.
    """
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'status': 'error',"message": "Both email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)


        if user is None:
            return Response({'status': 'error', "message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        
        elif not user.is_active:
            return Response({'status':'error', "message": "Please verify your email address."})


        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            'status': 'success',
            'access_token': str(access_token),
            'data': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class AdminLoginView(APIView):
    """
    Handle user login.
    """
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'status': 'error',"message": "Both email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)

        if user.is_superuser is False:
            return Response({'status': 'error', "message": "You are not authorized to access this resource."}, status=status.HTTP_403_FORBIDDEN)

        if user is None:
            return Response({'status': 'error', "message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'status': 'error', "message": "Your account is inactive."}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            'status': 'success',
            'access_token': str(access_token),
            'data': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class SignupView(APIView):
    """
    Handle user signup.
    """
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        if not email or not password :
            return Response({'status':'error',"message": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        elif User.objects.filter(email=email).exists():
            return Response({'status':'error',"message": "The email is already taken."}, status=status.HTTP_400_BAD_REQUEST)

        elif password != confirm_password:
            return Response({'status':'error',"message": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            pass
        send_email = False
        user = User(email=email)
        otp = ''.join(random.choices(string.digits, k=6))
        try:
            user.set_password(password)
            user.otp = otp
            user.otp_expired = timezone.now() + timedelta(minutes=5)
            user.save()
            send_email = send_otp(email, otp)
        except:
            return Response({'status':'error',"message": "Failed to create user. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        
        if send_email:
            return Response({
            'status': 'success',
            'message': 'Please check your email to get verification code.',
        }, status=status.HTTP_201_CREATED)
        else:
            return Response({'status': 'error',"message": "Failed to send OTP email. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({"error": "Both email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)
        if timezone.now() > user.otp_expired:
            return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
        # if user.is_active:
        #     return Response(
        #         {"status": "error", "message": "Email already verified."},
        #         status=status.HTTP_200_OK,
        #     )

        elif str(user.otp) == otp:
            user.is_active = True
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            return Response(
                {"status": "success", "access_token": access_token, "message": "Email verified successfully."},
                status=status.HTTP_200_OK,
            )
        return Response({"status": "error", "message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)


class SendOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)
        
        otp = ''.join(random.choices(string.digits, k=6))
        user.otp = otp
        user.otp_expired = timezone.now() + timedelta(minutes=5)
        user.save()
        send_email = send_otp(email, otp)  # Assuming `send_otp` handles sending the OTP via email

        if send_email:
            return Response(
                {"status": "success", "message": "We sent you an OTP to your email."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"status": "error", "message": "Failed to send OTP email. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        email = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            return Response(
                {'status': 'error', "message": "Please provide all required password fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {'status': 'error', "message": "New passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(email=email, password=old_password)
        print(email)
        if user is None:
            return Response(
                {'status': 'error', "message": "Invalid old password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {'status': 'success', "message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    permission_classes = [IsAuthenticated]  # Adjust permission as per your requirement
    def post(self, request):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        if not new_password or not confirm_password:
            return Response(
                {'status': 'error', "message": "All field are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif new_password != confirm_password:
            return Response(
                {'status': 'error', "message": "password do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif new_password == confirm_password:
            user = request.user
            user.set_password(new_password)
            user.save()
            return Response(
                {'status': 'success', "message": "successfully reset password"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {'status': 'error', "message": "something went wrong."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_profile = request.user  # Access the current logged-in user
            serializer = UserSerializer(user_profile)  # Serialize the user data
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'status': 'error',"message": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
        
    def patch(self, request):
        user = request.user  # Get the current logged-in user
        data = request.data.copy()  
        data['user'] = user.id 
        pickup_location_lat = request.data.get('pickup_location_lat', '')
        pickup_location_lng = request.data.get('pickup_location_lng', '')

        # Check if the location already exists
        check_location = UserPickupLocation.objects.filter(
            user=user,
            pickup_location_lat=pickup_location_lat,
            pickup_location_lng=pickup_location_lng
        )
        if check_location.exists():
            return Response({"error": "Address already exists"}, status=status.HTTP_400_BAD_REQUEST)

        geolocator = Nominatim(user_agent="CarPoolingApp")
        try:
            location = geolocator.reverse(f"{pickup_location_lat}, {pickup_location_lng}", exactly_one=True, language="en")
            if location:
                # Parse address into components
                address_details = location.raw.get('address', {})
                # Shorten the address by selecting key components
                short_address = ", ".join([
                    address_details.get('house_number'),
                    address_details.get('road'),
                    address_details.get('suburb'),
                    address_details.get('city'),
                    address_details.get('country')
                ]).strip(", ")
                data['address'] = short_address
            else:
                data['address'] = None
        except Exception as e:
            print(f"Geolocation Error: {e}")
            data['address'] = None
        
        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Save pickup location if provided
            if pickup_location_lat and pickup_location_lng:
                UserPickupLocation.objects.create(
                    user=user,
                    address=data['address'],
                    pickup_location_lat=pickup_location_lat,
                    pickup_location_lng=pickup_location_lng
                )
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
        
        return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class CustomerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            try:
                customer = User.objects.get(pk=pk)
                serializer = UserSerializer(customer)
                return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({"status": "error", "message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        customers = User.objects.all()
        all_customers = User.objects.all().count()
        serializer = UserSerializer(customers, many=True)
        return Response({"status": "success", "total": all_customers, "data": serializer.data}, status=status.HTTP_200_OK)


    def delete(self, request, pk=None):
        try:
            customer = User.objects.get(pk=pk)
            customer.delete()
            return Response({"status": "success", "message": "Customer deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({"status": "error", "message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)


class LocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        user = request.user
        if pk:
            try:
                location = UserPickupLocation.objects.get(pk=pk,user=user)
                serializer = pickupLocationSerializer(location)
                return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
            except:
                return Response({"status": "error", "message": "Pickup Location not found"}, status=status.HTTP_404_NOT_FOUND)

        location = UserPickupLocation.objects.filter(user=user)
        serializer = pickupLocationSerializer(location, many=True)
        return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user  
        data = request.data.copy()  
        data['user'] = user.id  
        pickup_location_lat = data.get('pickup_location_lat', '')
        pickup_location_lng = data.get('pickup_location_lng', '')
        if not pickup_location_lat or not pickup_location_lng:
            return Response({"status": "error", "message": "Pickup location latitude and longitude are required"}, status=status.HTTP_400_BAD_REQUEST)
        check_location = UserPickupLocation.objects.filter(user=user,pickup_location_lat=pickup_location_lat,pickup_location_lng=pickup_location_lng)
        if check_location:
            return Response({"status": "error", "message": "Pickup location already exists"}, status=status.HTTP_400_BAD_REQUEST)
        # Use Nominatim to get the address from latitude and longitude
        geolocator = Nominatim(user_agent="CarPoolingApp")
        try:
            location = geolocator.reverse(f"{pickup_location_lat}, {pickup_location_lng}", exactly_one=True, language="en")
            if location:
                # Parse address into components
                address_details = location.raw.get('address', {})
                # Shorten the address
                short_address = ", ".join(filter(None, [
                    address_details.get('house_number'),
                    address_details.get('road'),
                    address_details.get('suburb'),
                    address_details.get('city'),
                    address_details.get('country')
                ]))
                data['address'] = short_address
            else:
                data['address'] = None
        except Exception as e:
            return Response({
                "status": "error", 
                "message": f"Failed to get address: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        serializer = pickupLocationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"status": "error", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        user = request.user 
        data = request.data.copy() 
        data['user'] = user.id  
        pickup_location_lat = data.get('pickup_location_lat', '')
        pickup_location_lng = data.get('pickup_location_lng', '')
        if not pickup_location_lat or not pickup_location_lng:
            return Response({"status": "error", "message": "Pickup location latitude and longitude are required"}, status=status.HTTP_400_BAD_REQUEST)
        check_location = UserPickupLocation.objects.filter(user=user,pickup_location_lat=pickup_location_lat,pickup_location_lng=pickup_location_lng)
        if check_location:
            return Response({"status": "error", "message": "Pickup location already exists"}, status=status.HTTP_400_BAD_REQUEST)
        # Use Nominatim to get the address from latitude and longitude
        geolocator = Nominatim(user_agent="CarPoolingApp")
        try:
            location = geolocator.reverse(f"{pickup_location_lat}, {pickup_location_lng}", exactly_one=True, language="en")
            address = location.address if location else None
        except Exception as e:
            return Response({"status": "error", "message": f"Failed to get address: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data['address'] = address
        if not pk:
            return Response({"status": "error", "message": "Location ID is required for update"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            location = UserPickupLocation.objects.get(pk=pk,user=user)
        except :
            return Response({"status": "error", "message": "Pickup Location not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = pickupLocationSerializer(location, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"status": "error", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        user = request.user
        try:
            location = UserPickupLocation.objects.get(pk=pk,user=user)
            location.delete()
            return Response({"status": "success", "message": "UserPickupLocation deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except:
            return Response({"status": "error", "message": "UserPickupLocation not found"}, status=status.HTTP_404_NOT_FOUND)



class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q', '').strip()

        users = User.objects.all()

        if query:
            users = users.filter(
                Q(full_name__icontains=query) |
                Q(email__icontains=query) |
                Q(contact_number__icontains=query)
            )

        results = []
        for user in users:
            # Convert profile picture to URL (to avoid binary decoding issues)
            profile_url = (
                request.build_absolute_uri(user.profile_picture.url)
                if user.profile_picture
                else None
            )

            results.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "profile_picture": profile_url,
                "role": user.role,
                "subscription_plan": user.subscription_plan,
                "contact_number": user.contact_number,
                "is_active": user.is_active,
            })

        return Response({
            "count": len(results),
            "data": results
        })