from django.db import models
from accounts.models import TimestampedModel

class AboutUs(TimestampedModel):
    title = models.CharField(max_length=200)
    content = models.TextField()

class PrivacyPolicy(TimestampedModel):
    title = models.CharField(max_length=200)
    content = models.TextField()

class TermsAndConditions(TimestampedModel):
    title = models.CharField(max_length=200)
    content = models.TextField()