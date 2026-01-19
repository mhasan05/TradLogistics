from django.db import models
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin
from django.utils import timezone
from accounts.manager import UserManager #import from account apps


class User(AbstractBaseUser,PermissionsMixin):
    class Meta:
        verbose_name_plural = "User"
    user_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=10)
    last_name = models.CharField(max_length=10)
    email = models.EmailField(max_length=100,unique=True)
    phone = models.CharField(max_length=11,unique=True)
    profile_image = models.ImageField(upload_to='profile_image',default='profile_image/default.jpg')
    role = models.CharField(max_length=10)
    otp = models.CharField(max_length=6,blank=True,null=True)
    otp_expired_on = models.DateTimeField(blank=True,null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email','role']

    objects = UserManager()

    def __str__(self):
        return str(self.first_name) + ' ' + str(self.last_name)
    

