from django.contrib import admin
from .models import (
    User, Department, Course, EducationThread
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    ... 


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    ... 

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    ... 
    

@admin.register(EducationThread)
class EducationThreadAdmin(admin.ModelAdmin):
    ... 
    
