from django.contrib import admin
from .models import (
    User, Department
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    ... 


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    ... 
