from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django import forms

from .models import *


# ---------------------------
# Custom User Creation Form
# ---------------------------

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("phone", "email", "first_name", "last_name", "role")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# ---------------------------
# Custom User Change Form
# ---------------------------

class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"


# ---------------------------
# Custom User Admin
# ---------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    list_display = (
        "phone",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "created_at",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )

    search_fields = ("phone", "email", "first_name", "last_name")
    ordering = ("-created_at",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (_("Basic Info"), {
            "fields": ("phone", "email", "password")
        }),
        (_("Personal Info"), {
            "fields": ("first_name", "last_name", "role")
        }),
        
        (_("Important Dates"), {
            "fields": ("created_at", "updated_at")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "phone",
                "email",
                "first_name",
                "last_name",
                "role",
                "password1",
                "password2",
                "is_active",
                "is_staff",
            ),
        }),
    )


admin.site.unregister(Group)
admin.site.register(EmailOTP)