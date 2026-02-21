from django.db import models

# Create your models here.
class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=255, default="Privacy Policy")
    content = models.TextField(help_text="Full privacy policy text in HTML or plain text")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_on']
        verbose_name_plural = "Privacy Policies"
        db_table = "privacy_policy"

    def __str__(self):
        return str(self.title)
    


class TermsAndCondition(models.Model):
    title = models.CharField(max_length=255, default="Terms and Conditions")
    content = models.TextField(help_text="Full terms and conditions text in HTML or plain text")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_on']
        verbose_name_plural = "Terms and Conditions"
        db_table = "terms_and_conditions"

    def __str__(self):
        return str(self.title)
    



class AboutUs(models.Model):
    title = models.CharField(max_length=255, default="About Us")
    content = models.TextField(help_text="Full about us text in HTML or plain text")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_on']
        verbose_name_plural = "About Us"
        db_table = "about_us"

    def __str__(self):
        return str(self.title)