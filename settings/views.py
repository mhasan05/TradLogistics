from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,AllowAny
from .models import PrivacyPolicy
from .serializers import *

class PrivacyPolicyListCreateAPIView(APIView):
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_object(self):
        try:
            return PrivacyPolicy.objects.all().first()
        except PrivacyPolicy.DoesNotExist:
            return None

    def get(self, request):
        policies = PrivacyPolicy.objects.all().order_by('-created_on')
        serializer = PrivacyPolicySerializer(policies, many=True)
        return Response({'status': 'success', 'data': serializer.data})

    def post(self, request):
        get_privacy_policy = PrivacyPolicy.objects.all()
        if get_privacy_policy:
            return Response({'status':'error','message':'data already exist.'})
        serializer = PrivacyPolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        policy = self.get_object()
        if not policy:
            return Response({'status': 'error', 'message': 'Privacy policy not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PrivacyPolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        policy = self.get_object()
        if not policy:
            return Response({'status': 'error', 'message': 'Privacy policy not found'}, status=status.HTTP_404_NOT_FOUND)
        policy.delete()
        return Response({'status': 'success', 'message': 'Privacy policy deleted'}, status=status.HTTP_204_NO_CONTENT)

class TermsAndConditionsListCreateAPIView(APIView):
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_object(self):
        try:
            return TermsAndCondition.objects.all().first()
        except TermsAndCondition.DoesNotExist:
            return None

    def get(self, request):
        terms = TermsAndCondition.objects.all().order_by('-created_on')
        serializer = TermsAndConditionSerializer(terms, many=True)
        return Response({'status': 'success', 'data': serializer.data})

    def post(self, request):
        get_terms = TermsAndCondition.objects.all()
        if get_terms:
            return Response({'status':'error','message':'data already exist.'})
        serializer = TermsAndConditionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        terms = self.get_object()
        if not terms:
            return Response({'status': 'error', 'message': 'Terms and conditions not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsAndConditionSerializer(terms, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        terms = self.get_object()
        if not terms:
            return Response({'status': 'error', 'message': 'Terms and conditions not found'}, status=status.HTTP_404_NOT_FOUND)
        terms.delete()
        return Response({'status': 'success', 'message': 'Terms and conditions deleted'}, status=status.HTTP_204_NO_CONTENT)
    
class AboutUsListCreateAPIView(APIView):
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_object(self):
        try:
            return AboutUs.objects.all().first()
        except AboutUs.DoesNotExist:
            return None

    def get(self, request):
        about_us = AboutUs.objects.all().order_by('-created_on')
        serializer = AboutUsSerializer(about_us, many=True)
        return Response({'status': 'success', 'data': serializer.data})

    def post(self, request):
        get_about_us = AboutUs.objects.all()
        if get_about_us:
            return Response({'status':'error','message':'data already exist.'})
        serializer = AboutUsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'status': 'error', 'message': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        about_us = self.get_object()
        if not about_us:
            return Response({'status': 'error', 'message': 'About us not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = AboutUsSerializer(about_us, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'data': serializer.data})
        return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        about_us = self.get_object()
        if not about_us:
            return Response({'status': 'error', 'message': 'About us not found'}, status=status.HTTP_404_NOT_FOUND)
        about_us.delete()
        return Response({'status': 'success', 'message': 'About us deleted'}, status=status.HTTP_204_NO_CONTENT)