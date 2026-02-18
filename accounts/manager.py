from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError('Users must have a phone')
        user = self.model(phone = phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone, password, **extra_fields):
        user = self.create_user(phone, password, **extra_fields)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        return user