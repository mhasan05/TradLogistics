from django.contrib import admin
from accounts.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

class UserhAdmin(UserAdmin):
    search_fields = ('username',)
admin.site.register(User,UserAdmin)
admin.site.unregister(Group)